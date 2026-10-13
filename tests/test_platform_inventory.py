import copy
import json
from datetime import datetime, timedelta, timezone

import pytest

from platform_inventory import PlatformStore, validate_snapshot, read_observations, project
from server import IntegrationsApi
from scripts.record_connection import record


def stamp(days=0):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace('+00:00', 'Z')


def snapshot():
    digest = 'a' * 64
    manifest = dict(manifest_key='control/manifests/test.json', manifest_sha256=digest,
                    raw_sha256=digest, bronze_sha256=digest)
    return dict(schema_version='solo-empire.platform-integrations.v1', captured_at=stamp(),
                platforms=[dict(id='codex-app', name='Codex', mcp_transports=['stdio'], docs_url='https://example.com/docs')],
                capabilities=[dict(platform_id='codex-app', app_id='gmail', channel='plugin', availability='available',
                                   entry_id='gmail', endpoint_url=None, evidence_url='https://example.com/catalog', captured_at=stamp())],
                lineage=dict(dataset='platform_integrations', **manifest, source_manifests=[dict(source_id='official', **manifest)]))


RECORDS = [dict(id='gmail', name='Gmail', category='email', status='live')]


def test_routes_unknown_and_stale():
    data = snapshot()
    rows = project(data, RECORDS, [], now=datetime.now(timezone.utc))['rows']
    assert rows[0]['recommended_route'] == 'plugin'
    assert rows[0]['connection']['authentication'] == 'unknown'
    data['capabilities'] = []
    assert project(data, RECORDS, [])['rows'][0]['recommended_route'] == 'unknown'
    data['captured_at'] = stamp(8)
    assert project(data, RECORDS, [])['rows'][0]['recommended_route'] == 'needs_review'


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(extra='no'),
    lambda d: d['lineage'].update(manifest_sha256='X'*64),
    lambda d: d['lineage'].update(manifest_key='control/manifests/../bad'),
    lambda d: d['capabilities'][0].update(evidence_url='https://u:p@example.com'),
    lambda d: d['capabilities'][0].update(endpoint_url='https://example.com?token=x'),
    lambda d: d.update(captured_at='2099-01-01T00:00:00Z'),
    lambda d: d['capabilities'].append(copy.deepcopy(d['capabilities'][0])),
])
def test_snapshot_validation(mutation):
    data = snapshot()
    validate_snapshot(data)
    mutation(data)
    with pytest.raises(ValueError):
        validate_snapshot(data)


def test_private_observations(tmp_path):
    path = tmp_path / 'observations.json'
    observation = dict(platform_id='codex-app', app_id='gmail', installation='installed',
                       authentication='unknown', health='unknown', checked_at=stamp(), evidence_id='owner-check-1')
    path.write_text(json.dumps(dict(schema_version='solo-empire.integration-connections.v1', observations=[observation])))
    path.chmod(0o600)
    assert read_observations(path)[0]['installation'] == 'installed'
    path.chmod(0o644)
    with pytest.raises(ValueError):
        read_observations(path)
    path.chmod(0o600)
    observation['evidence_id'] = None
    path.write_text(json.dumps(dict(schema_version='solo-empire.integration-connections.v1', observations=[observation])))
    with pytest.raises(ValueError):
        read_observations(path)
    link = tmp_path / 'link'
    link.symlink_to(path)
    with pytest.raises(ValueError):
        read_observations(link)


def test_endpoint_auth_filters_and_fixed_unavailable(tmp_path):
    registry = tmp_path / 'registry.ts'
    registry.write_text("export const EXTERNAL_APP_REGISTRY = [\n{ id: 'gmail', name: 'Gmail', category: 'email', status: 'live', apiDocs: 'https://example.com' },\n];")
    path = tmp_path / 'snapshot.json'
    path.write_text(json.dumps(snapshot()))
    api = IntegrationsApi(registry, platform_snapshot_path=path, connections_path=tmp_path/'missing', token='fixture')
    target = '/api/v1/integrations/platforms'
    assert api.handle('GET', target).status == 401
    headers = {'Authorization': 'Bearer fixture'}
    response = api.handle('GET', target+'?platform=codex-app&app=gmail&route=plugin', headers=headers)
    assert response.status == 200 and len(response.payload['rows']) == 1
    assert api.handle('GET', target+'?platform=no-such', headers=headers).status == 400
    for query in ('route=bad', 'app=unknown-app', 'platform=codex-app&platform=codex-app', 'actor=owner', 'q='+'x'*81):
        assert api.handle('GET', target+'?'+query, headers=headers).status == 400
    assert api.handle('POST', target, headers=headers).status == 405
    observation_path = tmp_path/'missing'
    observation_path.write_text('{"credentials":"throwaway-forbidden-field"}')
    observation_path.chmod(0o600)
    assert api.handle('GET', target, headers=headers).status == 503
    observation_path.unlink()
    path.write_text('{}')
    response = api.handle('GET', target, headers=headers)
    assert response.status == 503 and response.payload['error']['code'] == 'platform_inventory_unavailable'


def test_priority_paused_and_explicit_unavailability():
    data = snapshot()
    base = data['capabilities'][0]
    data['capabilities'] += [dict(base, channel='connector'), dict(base, channel='manual_mcp')]
    assert project(data, RECORDS, [])['rows'][0]['recommended_route'] == 'plugin'
    data['capabilities'][0]['availability'] = 'unavailable'
    assert project(data, RECORDS, [])['rows'][0]['recommended_route'] == 'connector'
    data['capabilities'][1]['availability'] = 'unavailable'
    assert project(data, RECORDS, [])['rows'][0]['recommended_route'] == 'manual_mcp'
    data['capabilities'][2]['availability'] = 'unavailable'
    assert project(data, RECORDS, [])['rows'][0]['recommended_route'] == 'unavailable'
    assert project(data, [dict(RECORDS[0], status='paused')], [])['rows'][0]['recommended_route'] == 'paused'
    data['capabilities'].append(dict(base, entry_id='conflicting', availability='available'))
    assert project(data, RECORDS, [])['rows'][0]['recommended_route'] == 'unknown'


def test_stale_observations_are_labelled_and_not_counted():
    observation = dict(platform_id='codex-app', app_id='gmail', installation='installed',
                       authentication='connected', health='verified', checked_at=stamp(8), evidence_id='check-1')
    payload = project(snapshot(), RECORDS, [observation])
    assert payload['rows'][0]['connection']['freshness'] == 'stale'
    assert payload['summary']['installed'] == payload['summary']['authenticated'] == payload['summary']['health_verified'] == 0
    observation['checked_at'] = stamp()
    assert project(snapshot(), RECORDS, [observation])['summary']['health_verified'] == 1


def test_atomic_cli_metadata_and_symlink_denial(tmp_path):
    path = tmp_path / '.runtime/connections.json'
    observation = dict(platform_id='codex-app', app_id='gmail', installation='installed',
                       authentication='unknown', health='unknown', checked_at=stamp(), evidence_id='check-1')
    record(path, observation)
    assert path.stat().st_mode & 0o777 == 0o600
    assert read_observations(path) == [observation]
    record(path, dict(observation, installation='not_installed'))
    assert len(read_observations(path)) == 1
    with pytest.raises(ValueError):
        record(path, dict(observation, token='throwaway-forbidden-field'))
    target = tmp_path / 'target'
    target.write_text('preserve')
    path.unlink()
    path.symlink_to(target)
    with pytest.raises(ValueError):
        record(path, observation)
    assert target.read_text() == 'preserve'


@pytest.mark.parametrize('url', ['http://example.com', 'https://example.com/#', 'https://example.com/?', 'https://example.com/\ud800'])
def test_bad_urls_fail_closed(url):
    data = snapshot()
    data['platforms'][0]['docs_url'] = url
    with pytest.raises(ValueError):
        validate_snapshot(data)


def test_duplicate_json_fields_fail_closed(tmp_path):
    path = tmp_path / 'snapshot'
    path.write_text('{"schema_version":"wrong","schema_version":"wrong"}')
    with pytest.raises(ValueError):
        PlatformStore(path, tmp_path/'missing').overview(RECORDS)


def test_lake_hive_manifest_keys():
    data = snapshot()
    key = 'control/manifests/source=official/batch_id=capture-1.json'
    data['lineage']['manifest_key'] = key
    data['lineage']['source_manifests'][0]['manifest_key'] = key
    validate_snapshot(data)
    for key in ('control/manifests/source=official/../bad', '/control/manifests/a', 'control/manifests//a', 'control/manifests/source=official/./a'):
        data['lineage']['manifest_key'] = key
        with pytest.raises(ValueError):
            validate_snapshot(data)
