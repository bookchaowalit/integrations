#!/usr/bin/env python3
"""Owner-local atomic metadata observation writer. No HTTP/provider writes."""
import argparse
import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from platform_inventory import CONNECTION_SCHEMA, read_observations, validate_observations


def record(path, observation):
    path = Path(path)
    validate_observations({'schema_version': CONNECTION_SCHEMA, 'observations': [observation]})
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Serialize owner CLI writers; the API only reads the atomically replaced file.
    fd = os.open(str(path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    with os.fdopen(fd, 'r+') as lock:
        info = os.fstat(lock.fileno())
        if info.st_uid != os.getuid() or info.st_mode & 0o777 != 0o600:
            raise ValueError('invalid owner lock')
        fcntl.flock(lock, fcntl.LOCK_EX)
        observations = read_observations(path)
        observations = [o for o in observations if (o['platform_id'], o['app_id']) != (observation['platform_id'], observation['app_id'])]
        observations.append(observation)
        data = {'schema_version': CONNECTION_SCHEMA, 'observations': observations}
        validate_observations(data)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.connections-', delete=False) as stream:
                temporary = stream.name
                os.fchmod(stream.fileno(), 0o600)
                json.dump(data, stream, sort_keys=True)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary:
                os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', default=os.environ.get('INTEGRATIONS_API_CONNECTIONS_PATH', str(Path(__file__).resolve().parents[1] / '.runtime/platform-connections.json')))
    parser.add_argument('--platform', required=True)
    parser.add_argument('--app', required=True)
    parser.add_argument('--installation', choices=['installed', 'not_installed', 'unknown'], default='unknown')
    parser.add_argument('--authentication', choices=['connected', 'disconnected', 'unknown'], default='unknown')
    parser.add_argument('--health', choices=['verified', 'failed', 'unknown'], default='unknown')
    parser.add_argument('--checked-at', default=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
    parser.add_argument('--evidence-id', required=True)
    args = parser.parse_args()
    try:
        record(args.path, dict(platform_id=args.platform, app_id=args.app, installation=args.installation,
                               authentication=args.authentication, health=args.health, checked_at=args.checked_at, evidence_id=args.evidence_id))
    except (OSError, ValueError, TypeError):
        parser.exit(1, 'Observation could not be recorded\n')
    print('Observation recorded')


if __name__ == '__main__':
    main()
