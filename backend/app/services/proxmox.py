import httpx
from app.core.config import settings


class ProxmoxClient:
    def __init__(self):
        self.base_url = settings.proxmox_base_url.rstrip('/')
        self.headers = {
            'Authorization': f'PVEAPIToken={settings.proxmox_token_id}={settings.proxmox_token_secret}'
        }

    async def list_nodes(self):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.get(f'{self.base_url}/nodes', headers=self.headers)
            r.raise_for_status()
            return r.json()['data']

    async def clone_vm(self, node: str, source_vmid: int, newid: int, name: str):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.post(
                f'{self.base_url}/nodes/{node}/qemu/{source_vmid}/clone',
                headers=self.headers,
                data={'newid': newid, 'name': name, 'full': 1},
            )
            r.raise_for_status()
            return r.json()

    async def start_vm(self, node: str, vmid: int):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.post(f'{self.base_url}/nodes/{node}/qemu/{vmid}/status/start', headers=self.headers)
            r.raise_for_status()
            return r.json()
