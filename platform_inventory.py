"""Strict lake-published capability snapshot and private metadata projection.

This module performs no network calls. Public catalogs never establish account state.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

SCHEMA = 'solo-empire.platform-integrations.v1'
CONNECTION_SCHEMA = 'solo-empire.integration-connections.v1'
CHANNELS = ('plugin', 'connector', 'manual_mcp')
ROUTES = (*CHANNELS, 'unknown', 'unavailable', 'paused', 'needs_review')
ID = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
HASH = re.compile(r'^[a-f0-9]{64}$')
EVIDENCE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$')
MAX_BYTES = 4 * 1024 * 1024


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise ValueError('invalid fields')


def identifier(value):
    if not isinstance(value, str) or len(value) > 80 or not ID.fullmatch(value):
        raise ValueError('invalid identifier')


def timestamp(value, now=None):
    if not isinstance(value, str) or len(value) > 40 or not value.endswith(('Z', '+00:00')):
        raise ValueError('invalid UTC timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError('invalid UTC timestamp') from None
    if parsed.utcoffset() != timedelta(0) or parsed > (now or datetime.now(timezone.utc)) + timedelta(minutes=5):
        raise ValueError('invalid timestamp')
    return parsed


def https(value):
    if not isinstance(value, str) or len(value) > 2048 or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        raise ValueError('invalid URL')
    value.encode('utf-8', errors='strict')
    parts = urlsplit(value)
    if parts.scheme != 'https' or not parts.hostname or parts.username is not None or parts.password is not None or parts.query or parts.fragment or '?' in value or '#' in value or '\\' in value:
        raise ValueError('invalid URL')
    if parts.port is not None and not 1 <= parts.port <= 65535:
        raise ValueError('invalid URL')


def manifest(value, source=False):
    fields(value, ('source_id' if source else 'dataset source_manifests') + ' manifest_key manifest_sha256 raw_sha256 bronze_sha256')
    if source:
        identifier(value['source_id'])
    elif value['dataset'] != 'platform_integrations':
        raise ValueError('invalid dataset')
    key = value['manifest_key']
    if not isinstance(key, str) or len(key) > 512 or not key.startswith('control/manifests/') or not re.fullmatch(r'[A-Za-z0-9_=./-]+', key) or any(p in ('', '.', '..') for p in key.split('/')) or PurePosixPath(key).is_absolute():
        raise ValueError('invalid manifest key')
    for name in ('manifest_sha256', 'raw_sha256', 'bronze_sha256'):
        if not isinstance(value[name], str) or not HASH.fullmatch(value[name]):
            raise ValueError('invalid checksum')


def validate_snapshot(data, now=None):
    fields(data, 'schema_version captured_at platforms capabilities lineage')
    if data['schema_version'] != SCHEMA:
        raise ValueError('invalid schema')
    captured = timestamp(data['captured_at'], now)
    if not isinstance(data['platforms'], list) or not 1 <= len(data['platforms']) <= 50:
        raise ValueError('invalid platforms')
    platforms = set()
    for p in data['platforms']:
        fields(p, 'id name mcp_transports docs_url')
        identifier(p['id'])
        if p['id'] in platforms or not isinstance(p['name'], str) or not 1 <= len(p['name']) <= 80 or any(ord(c) < 32 for c in p['name']):
            raise ValueError('invalid platform')
        platforms.add(p['id'])
        p['name'].encode('utf-8', errors='strict')
        transports = p['mcp_transports']
        if not isinstance(transports, list) or any(t not in ('stdio', 'sse', 'streamable_http') for t in transports) or len(set(transports)) != len(transports):
            raise ValueError('invalid transports')
        https(p['docs_url'])
    if not isinstance(data['capabilities'], list) or len(data['capabilities']) > 20000:
        raise ValueError('invalid capabilities')
    seen = set()
    for c in data['capabilities']:
        fields(c, 'platform_id app_id channel availability entry_id endpoint_url evidence_url captured_at')
        identifier(c['platform_id'])
        identifier(c['app_id'])
        if c['platform_id'] not in platforms or c['channel'] not in CHANNELS or c['availability'] not in ('available', 'unavailable', 'unknown'):
            raise ValueError('invalid capability')
        if c['entry_id'] is not None and (not isinstance(c['entry_id'], str) or not EVIDENCE.fullmatch(c['entry_id'])):
            raise ValueError('invalid entry')
        grain = (c['platform_id'], c['app_id'], c['channel'], c['entry_id'])
        if grain in seen:
            raise ValueError('duplicate capability')
        seen.add(grain)
        if c['endpoint_url'] is not None:
            https(c['endpoint_url'])
        https(c['evidence_url'])
        if timestamp(c['captured_at'], now) > captured + timedelta(minutes=5):
            raise ValueError('invalid capability capture')
    manifest(data['lineage'])
    sources = data['lineage']['source_manifests']
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise ValueError('invalid source manifests')
    seen = set()
    for source in sources:
        manifest(source, True)
        if source['source_id'] in seen:
            raise ValueError('duplicate source')
        seen.add(source['source_id'])
    return data


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field')
        result[key] = value
    return result


def decode(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('file too large')
    return json.loads(raw, object_pairs_hook=unique_object)


def validate_observations(data, now=None):
    fields(data, 'schema_version observations')
    if data['schema_version'] != CONNECTION_SCHEMA or not isinstance(data['observations'], list) or len(data['observations']) > 20000:
        raise ValueError('invalid observations')
    seen = set()
    for o in data['observations']:
        fields(o, 'platform_id app_id installation authentication health checked_at evidence_id')
        identifier(o['platform_id'])
        identifier(o['app_id'])
        grain = (o['platform_id'], o['app_id'])
        if grain in seen:
            raise ValueError('duplicate observation')
        seen.add(grain)
        for key, options in [('installation', ('installed', 'not_installed', 'unknown')), ('authentication', ('connected', 'disconnected', 'unknown')), ('health', ('verified', 'failed', 'unknown'))]:
            if o[key] not in options:
                raise ValueError('invalid observation state')
        if o['checked_at'] is not None:
            timestamp(o['checked_at'], now)
        if o['evidence_id'] is not None and (not isinstance(o['evidence_id'], str) or not EVIDENCE.fullmatch(o['evidence_id'])):
            raise ValueError('invalid evidence identifier')
        if any(o[k] != 'unknown' for k in ('installation', 'authentication', 'health')) and (o['checked_at'] is None or o['evidence_id'] is None):
            raise ValueError('observation evidence required')
    return data['observations']


def read_observations(path):
    path = Path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return []
    except OSError:
        raise ValueError('invalid observation file') from None
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
            raise ValueError('observations must be owner-only')
        return validate_observations(decode(stream.read(MAX_BYTES + 1)))


def freshness(value, now):
    return 'stale' if now - timestamp(value, now) > timedelta(days=7) else 'fresh'


def project(data, records, observations, *, now=None, revision=None):
    now = now or datetime.now(timezone.utc)
    validate_snapshot(data, now)
    validate_observations({'schema_version': CONNECTION_SCHEMA, 'observations': observations}, now)
    age = freshness(data['captured_at'], now)
    observed = {(o['platform_id'], o['app_id']): o for o in observations}
    grouped = {}
    for c in data['capabilities']:
        grouped.setdefault((c['platform_id'], c['app_id'], c['channel']), []).append(c)
    rows = []
    for p in data['platforms']:
        for app in records:
            channels = {}
            for channel in CHANNELS:
                entries = grouped.get((p['id'], app['id'], channel), [])
                values = {e['availability'] for e in entries}
                availability = 'available' if 'available' in values and 'unavailable' not in values else 'unavailable' if values == {'unavailable'} else 'unknown'
                channels[channel] = {'availability': availability, 'entries': entries}
            route = next((c for c in CHANNELS if channels[c]['availability'] == 'available'), 'unavailable' if all(channels[c]['availability'] == 'unavailable' for c in CHANNELS) else 'unknown')
            if age == 'stale' or any(freshness(e['captured_at'], now) == 'stale' for e in channels.get(route, {}).get('entries', [])):
                route = 'needs_review'
            if app['status'] == 'paused':
                route = 'paused'
            o = observed.get((p['id'], app['id']))
            connection = {k: o[k] if o else ('unknown' if k in ('installation', 'authentication', 'health') else None) for k in ('installation', 'authentication', 'health', 'checked_at', 'evidence_id')}
            connection['freshness'] = freshness(o['checked_at'], now) if o and o['checked_at'] else 'unknown'
            rows.append({'id': p['id'] + ':' + app['id'], 'platform_id': p['id'], 'app_id': app['id'], 'app_name': app['name'], 'category': app['category'], 'registry_status': app['status'], 'channels': channels, 'recommended_route': route, 'connection': connection})
    summary = {'rows_total': len(rows), 'rows_matched': len(rows),
               'native_available': sum(any(r['channels'][c]['availability'] == 'available' for c in ('plugin', 'connector')) for r in rows),
               'manual_mcp_available': sum(r['channels']['manual_mcp']['availability'] == 'available' for r in rows)}
    for label, key, state in [('installed', 'installation', 'installed'), ('authenticated', 'authentication', 'connected'), ('health_verified', 'health', 'verified')]:
        summary[label] = sum(r['connection'][key] == state and r['connection']['freshness'] == 'fresh' for r in rows)
    for route in ('paused', 'unknown', 'needs_review'):
        summary[route] = sum(r['recommended_route'] == route for r in rows)
    return {'schema_version': SCHEMA, 'generated_at': now.isoformat().replace('+00:00', 'Z'),
            'snapshot': {'captured_at': data['captured_at'], 'freshness': age, 'revision': revision or hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest(), 'lineage': data['lineage']},
            'platforms': data['platforms'], 'summary': summary, 'rows': rows}


class PlatformStore:
    def __init__(self, path, connections_path):
        self.path, self.connections_path = Path(path), Path(connections_path)

    def overview(self, records):
        with self.path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        return project(decode(raw), records, read_observations(self.connections_path), revision=hashlib.sha256(raw).hexdigest())
