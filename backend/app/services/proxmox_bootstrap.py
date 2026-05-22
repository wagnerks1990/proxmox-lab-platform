from datetime import datetime
import httpx
from sqlalchemy.orm import Session

from app.models.models import ProxmoxCluster, ProxmoxNode, ProxmoxClusterDefault
from app.services.secret_crypto import encrypt_secret, decrypt_secret


TOKEN_ID_DEFAULT = 'proxmox-lab-platform'


class ProxmoxBootstrapService:
    def __init__(self, db: Session):
        self.db = db

    async def bootstrap_with_root(self, payload: dict) -> dict:
        api_url = payload['api_url'].rstrip('/')
        verify_ssl = bool(payload.get('verify_ssl', False))
        root_username = payload.get('root_username', 'root@pam')
        root_password = payload['root_password']
        cluster_name = payload['name']
        token_id = payload.get('token_id') or TOKEN_ID_DEFAULT

        steps = []
        auth_ticket = await self._login(api_url, verify_ssl, root_username, root_password)
        steps.append({'step': 'root_authentication', 'status': 'success'})

        resources = await self._get_resources(api_url, verify_ssl, auth_ticket)
        steps.append({'step': 'resource_read', 'status': 'success', 'count': len(resources)})

        token_secret, created = await self._ensure_token(api_url, verify_ssl, auth_ticket, root_username, token_id)
        steps.append({'step': 'token_setup', 'status': 'success', 'created': created})

        cluster = self.db.query(ProxmoxCluster).filter(ProxmoxCluster.name == cluster_name).first()
        if cluster is None:
            cluster = ProxmoxCluster(name=cluster_name)
            self.db.add(cluster)

        cluster.api_url = api_url
        cluster.verify_ssl = verify_ssl
        cluster.auth_mode = 'token'
        cluster.root_username = root_username
        cluster.token_user = root_username
        cluster.token_id = token_id
        cluster.encrypted_token_secret = encrypt_secret(token_secret)
        cluster.token_created_by_app = created
        cluster.last_validated_at = datetime.utcnow()
        cluster.last_validation_status = 'success'
        cluster.last_validation_error = None

        self.db.query(ProxmoxNode).filter(ProxmoxNode.cluster_id == cluster.id).delete()
        self.db.flush()

        node_count = 0
        for item in resources:
            if item.get('type') == 'node':
                node_count += 1
                self.db.add(ProxmoxNode(cluster_id=cluster.id, node_name=item.get('node'), status=item.get('status'), raw_summary_json=str(item)))

        defaults = self.db.query(ProxmoxClusterDefault).filter(ProxmoxClusterDefault.cluster_id == cluster.id).first()
        if defaults is None:
            self.db.add(ProxmoxClusterDefault(cluster_id=cluster.id))

        self.db.commit()
        self.db.refresh(cluster)
        return {
            'cluster_id': cluster.id,
            'name': cluster.name,
            'api_url': cluster.api_url,
            'verify_ssl': cluster.verify_ssl,
            'token_user': cluster.token_user,
            'token_id': cluster.token_id,
            'token_created_by_app': cluster.token_created_by_app,
            'nodes_discovered': node_count,
            'steps': steps,
        }

    async def validate_cluster(self, cluster: ProxmoxCluster) -> dict:
        secret = decrypt_secret(cluster.encrypted_token_secret) if cluster.encrypted_token_secret else None
        if not secret:
            return {'ok': False, 'error': 'missing token secret'}
        headers = {'Authorization': f'PVEAPIToken={cluster.token_user}!{cluster.token_id}={secret}'}
        async with httpx.AsyncClient(verify=cluster.verify_ssl, timeout=20) as client:
            r = await client.get(f"{cluster.api_url}/nodes", headers=headers)
            r.raise_for_status()
            nodes = r.json().get('data', [])
        return {'ok': True, 'nodes_count': len(nodes)}

    async def _login(self, api_url: str, verify_ssl: bool, username: str, password: str) -> dict:
        async with httpx.AsyncClient(verify=verify_ssl, timeout=20) as client:
            r = await client.post(f'{api_url}/access/ticket', data={'username': username, 'password': password})
            r.raise_for_status()
            data = r.json().get('data', {})
            return {'ticket': data.get('ticket'), 'csrf': data.get('CSRFPreventionToken')}

    async def _get_resources(self, api_url: str, verify_ssl: bool, auth: dict) -> list[dict]:
        cookies = {'PVEAuthCookie': auth['ticket']}
        headers = {'CSRFPreventionToken': auth['csrf']}
        async with httpx.AsyncClient(verify=verify_ssl, timeout=20, cookies=cookies, headers=headers) as client:
            r = await client.get(f'{api_url}/cluster/resources')
            r.raise_for_status()
            return r.json().get('data', [])

    async def _ensure_token(self, api_url: str, verify_ssl: bool, auth: dict, user: str, token_id: str):
        cookies = {'PVEAuthCookie': auth['ticket']}
        headers = {'CSRFPreventionToken': auth['csrf']}
        async with httpx.AsyncClient(verify=verify_ssl, timeout=20, cookies=cookies, headers=headers) as client:
            r = await client.post(f'{api_url}/access/users/{user}/token/{token_id}', data={'privsep': 0})
            if r.status_code in (409, 400):
                raise RuntimeError('Token already exists. Delete and rerun bootstrap, or use manual token entry.')
            r.raise_for_status()
            secret = r.json().get('data', {}).get('value')
            if not secret:
                raise RuntimeError('Token was created but secret was not returned by Proxmox')
            return secret, True
