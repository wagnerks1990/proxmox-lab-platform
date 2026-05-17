import base64
from dataclasses import dataclass

import httpx

from app.core.config import settings


class GuacamoleError(Exception):
    pass


@dataclass
class GuacamoleAuth:
    token: str
    datasource: str


def guacamole_configured() -> bool:
    return bool(
        settings.guacamole_internal_url
        and settings.guacamole_base_url
        and settings.guacamole_admin_user
        and settings.guacamole_admin_password
    )


async def check_guacamole_reachable(timeout: float = 2.5) -> tuple[bool, str | None]:
    url = settings.guacamole_internal_url.rstrip('/') + '/'
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=settings.guacamole_verify_ssl) as c:
            r = await c.get(url)
        if r.status_code < 500:
            return True, None
        return False, f'HTTP {r.status_code}'
    except Exception as exc:
        return False, str(exc)


def _build_base_url() -> str:
    return settings.guacamole_internal_url.rstrip('/')


def _build_public_base_url() -> str:
    return (settings.guacamole_base_url or '/guacamole').rstrip('/')


async def _auth(client: httpx.AsyncClient) -> GuacamoleAuth:
    r = await client.post(
        f'{_build_base_url()}/api/tokens',
        data={'username': settings.guacamole_admin_user, 'password': settings.guacamole_admin_password},
    )
    if r.status_code >= 400:
        raise GuacamoleError(f'Authentication failed: HTTP {r.status_code}')
    payload = r.json()
    token = payload.get('authToken')
    datasource = settings.guacamole_datasource or payload.get('dataSource')
    if not token or not datasource:
        raise GuacamoleError('Guacamole authentication response missing authToken or dataSource')
    return GuacamoleAuth(token=token, datasource=datasource)


def _encode_client_id(connection_id: str, datasource: str) -> str:
    return base64.b64encode(f'{connection_id}\x00c\x00{datasource}'.encode('utf-8')).decode('utf-8')


async def create_or_update_connection(vm, protocol: str) -> tuple[str, str]:
    hostname = vm.assigned_ip or vm.hostname
    if not hostname:
        raise GuacamoleError('VM has no reachable hostname/IP for Guacamole connection')
    port = 3389 if protocol == 'rdp' else (5900 if protocol == 'vnc' else 22)
    conn_name = f'vm-{vm.vmid}-{protocol}'

    async with httpx.AsyncClient(timeout=10.0, verify=settings.guacamole_verify_ssl) as client:
        auth = await _auth(client)
        endpoint = f'{_build_base_url()}/api/session/data/{auth.datasource}/connections'
        params = {'token': auth.token}
        existing = await client.get(endpoint, params=params)
        if existing.status_code >= 400:
            raise GuacamoleError(f'Failed listing connections: HTTP {existing.status_code}')
        existing_map = existing.json() or {}

        target_id = None
        for cid, conn in existing_map.items():
            if conn.get('name') == conn_name:
                target_id = str(cid)
                break

        payload = {
            'parentIdentifier': 'ROOT',
            'name': conn_name,
            'protocol': protocol,
            'parameters': {'hostname': hostname, 'port': str(port), 'username': vm.default_username or ''},
            'attributes': {},
        }

        if target_id:
            upd = await client.put(f'{endpoint}/{target_id}', params=params, json=payload)
            if upd.status_code >= 400:
                raise GuacamoleError(f'Failed updating connection: HTTP {upd.status_code}')
        else:
            create = await client.post(endpoint, params=params, json=payload)
            if create.status_code >= 400:
                raise GuacamoleError(f'Failed creating connection: HTTP {create.status_code}')
            target_id = str(create.json().get('identifier') or create.json().get('id'))
            if not target_id:
                raise GuacamoleError('Guacamole create connection response missing identifier')

    return target_id, _encode_client_id(target_id, auth.datasource)


async def build_launch_payload(vm, protocol: str) -> dict:
    if protocol not in ['rdp', 'vnc', 'ssh']:
        raise GuacamoleError('Unsupported protocol')

    async with httpx.AsyncClient(timeout=10.0, verify=settings.guacamole_verify_ssl) as client:
        auth = await _auth(client)
    connection_id, encoded = await create_or_update_connection(vm, protocol)
    launch_url = f"{_build_public_base_url()}/#/client/{encoded}?token={auth.token}"
    return {
        'enabled': True,
        'protocol': protocol,
        'launch_url': launch_url,
        'connection_id': connection_id,
        'expires_note': 'Guacamole token lifetime is managed by Guacamole',
    }
