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

    async def get_novnc_ticket(self, node: str, vmid: int):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.post(f'{self.base_url}/nodes/{node}/qemu/{vmid}/vncproxy', headers=self.headers, data={'websocket': 1})
            r.raise_for_status()
            return r.json().get('data', {})

    async def get_spice_config(self, node: str, vmid: int):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.post(f'{self.base_url}/nodes/{node}/qemu/{vmid}/spiceproxy', headers=self.headers)
            r.raise_for_status()
            return r.json().get('data', '')

    async def get_guest_network(self, node: str, vmid: int):
        async with httpx.AsyncClient(verify=settings.proxmox_verify_ssl, timeout=30) as client:
            r = await client.get(f'{self.base_url}/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces', headers=self.headers)
            r.raise_for_status()
            return r.json().get('data', {}).get('result', [])


    @staticmethod
    def _is_primary_iface(name: str) -> bool:
        n = (name or '').lower()
        return n.startswith(('ens', 'eth', 'enp', 'eno', 'wlan'))

    @staticmethod
    def parse_guest_agent_ip(interfaces: list[dict]) -> tuple[str | None, dict]:
        ignored = []
        candidates_primary = []
        candidates_other = []
        for iface in interfaces or []:
            name = iface.get('name', '')
            lname = name.lower()
            is_primary = ProxmoxClient._is_primary_iface(name)
            for addr in iface.get('ip-addresses', []):
                ip = (addr.get('ip-address') or '').strip()
                kind = addr.get('ip-address-type')
                if not ip:
                    ignored.append({'interface': name, 'ip': ip, 'reason': 'empty'})
                    continue
                if kind != 'ipv4':
                    if ip.startswith('fe80:'):
                        ignored.append({'interface': name, 'ip': ip, 'reason': 'link-local ipv6'})
                    continue
                if ip.startswith('127.'):
                    ignored.append({'interface': name, 'ip': ip, 'reason': 'loopback'})
                    continue
                if lname.startswith(('lo', 'docker', 'cni', 'br-', 'virbr', 'veth', 'podman')):
                    ignored.append({'interface': name, 'ip': ip, 'reason': 'container/bridge interface'})
                    continue
                (candidates_primary if is_primary else candidates_other).append({'interface': name, 'ip': ip})

        chosen = (candidates_primary[0]['ip'] if candidates_primary else (candidates_other[0]['ip'] if candidates_other else None))
        diag = {
            'interfaces': [i.get('name') for i in interfaces or []],
            'usable_candidates': candidates_primary + candidates_other,
            'ignored_addresses': ignored,
            'discovered_ip': chosen,
        }
        return chosen, diag

    async def get_vm_guest_ip(self, node: str, vmid: int) -> str | None:
        try:
            interfaces = await self.get_guest_network(node, vmid)
            ip, _ = self.parse_guest_agent_ip(interfaces)
            return ip
        except Exception:
            return None

    async def get_vm_guest_agent_diagnostics(self, node: str, vmid: int) -> dict:
        try:
            interfaces = await self.get_guest_network(node, vmid)
            ip, diag = self.parse_guest_agent_ip(interfaces)
            return {'agent_reachable': True, 'discovered_ip': ip, **diag}
        except Exception as exc:
            return {'agent_reachable': False, 'discovered_ip': None, 'interfaces': [], 'usable_candidates': [], 'ignored_addresses': [], 'error': str(exc)}
