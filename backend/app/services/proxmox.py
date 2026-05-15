import asyncio
import httpx
from fastapi import HTTPException
from app.core.config import settings


class ProxmoxClient:
    def __init__(self):
        self.base_url = settings.proxmox_base_url.rstrip('/')
        self.headers = {
            'Authorization': f'PVEAPIToken={settings.proxmox_token_id}={settings.proxmox_token_secret}'
        }

    async def _request(self, method: str, path: str, **kwargs):
        try:
            async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
                r = await client.request(method, f'{self.base_url}{path}', headers=self.headers, **kwargs)
                r.raise_for_status()
                return r.json().get('data')
        except httpx.HTTPStatusError as exc:
            detail = 'Proxmox request failed'
            try:
                payload = exc.response.json()
                detail = payload.get('errors') or payload.get('message') or detail
            except Exception:
                detail = exc.response.text or detail
            raise HTTPException(status_code=502, detail={'message': 'Proxmox API error', 'details': str(detail)})
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail={'message': 'Proxmox API unavailable', 'details': str(exc)})

    async def clone_vm(self, node: str, source_vmid: int, newid: int, name: str):
        return await self._request(
            'POST',
            f'/nodes/{node}/qemu/{source_vmid}/clone',
            data={'newid': newid, 'name': name, 'full': 1},
        )

    async def start_vm(self, node: str, vmid: int):
        return await self._request('POST', f'/nodes/{node}/qemu/{vmid}/status/start')

    async def stop_vm(self, node: str, vmid: int):
        return await self._request('POST', f'/nodes/{node}/qemu/{vmid}/status/stop')

    async def reboot_vm(self, node: str, vmid: int):
        return await self._request('POST', f'/nodes/{node}/qemu/{vmid}/status/reboot')

    async def delete_vm(self, node: str, vmid: int):
        return await self._request('DELETE', f'/nodes/{node}/qemu/{vmid}')

    async def get_vm_status(self, node: str, vmid: int):
        return await self._request('GET', f'/nodes/{node}/qemu/{vmid}/status/current')

    async def wait_for_task(self, node: str, upid: str, timeout_seconds: int = 120):
        max_attempts = max(1, timeout_seconds // 2)
        for _ in range(max_attempts):
            task = await self._request('GET', f'/nodes/{node}/tasks/{upid}/status')
            if task and task.get('status') == 'stopped':
                if task.get('exitstatus') != 'OK':
                    raise HTTPException(status_code=502, detail={'message': 'Proxmox task failed', 'details': task.get('exitstatus', 'unknown')})
                return task
            await asyncio.sleep(2)
        raise HTTPException(status_code=504, detail={'message': 'Proxmox task timeout', 'details': f'UPID {upid}'})
