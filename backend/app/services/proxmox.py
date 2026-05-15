import asyncio
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
        return await self._vm_action(node, vmid, 'start')

    async def stop_vm(self, node: str, vmid: int):
        return await self._vm_action(node, vmid, 'stop')

    async def reboot_vm(self, node: str, vmid: int):
        return await self._vm_action(node, vmid, 'reboot')

    async def delete_vm(self, node: str, vmid: int):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.delete(f'{self.base_url}/nodes/{node}/qemu/{vmid}', headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def get_vm_status(self, node: str, vmid: int):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.get(f'{self.base_url}/nodes/{node}/qemu/{vmid}/status/current', headers=self.headers)
            r.raise_for_status()
            return r.json()['data']

    async def wait_for_task(self, node: str, upid: str, timeout_seconds: int = 120):
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while True:
            async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
                r = await client.get(f'{self.base_url}/nodes/{node}/tasks/{upid}/status', headers=self.headers)
                r.raise_for_status()
                task = r.json()['data']
            if task.get('status') == 'stopped':
                return task
            if asyncio.get_event_loop().time() > deadline:
                raise TimeoutError(f'Timed out waiting for Proxmox task {upid}')
            await asyncio.sleep(2)

    async def _vm_action(self, node: str, vmid: int, action: str):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.post(f'{self.base_url}/nodes/{node}/qemu/{vmid}/status/{action}', headers=self.headers)
            r.raise_for_status()
            return r.json()
