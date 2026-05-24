from __future__ import annotations

import httpx
from app.services.proxmox import ProxmoxClient


class ProxmoxAssetsService:
    def __init__(self):
        self.client = ProxmoxClient()

    async def _get(self, path: str, params: dict | None = None):
        async with httpx.AsyncClient(verify=self.client.verify_ssl, timeout=60, headers=self.client.headers) as http:
            r = await http.get(f'{self.client.base_url}{path}', params=params)
            r.raise_for_status()
            return r.json().get('data', [])

    async def _post(self, path: str, data: dict):
        async with httpx.AsyncClient(verify=self.client.verify_ssl, timeout=120, headers=self.client.headers) as http:
            r = await http.post(f'{self.client.base_url}{path}', data=data)
            r.raise_for_status()
            return r.json().get('data')

    async def discover_nodes(self):
        rows = await self._get('/nodes')
        return [{'node': x.get('node'), 'status': x.get('status')} for x in rows]

    async def discover_isos_by_node(self, nodes: list[str], storage_id: str = 'local'):
        out = []
        for node in nodes:
            rows = await self._get(f'/nodes/{node}/storage/{storage_id}/content', {'content': 'iso'})
            out.append({
                'node': node,
                'storage_id': storage_id,
                'content_type': 'iso',
                'items': [
                    {
                        'volid': r.get('volid'),
                        'filename': (r.get('volid') or '').split('/')[-1] if r.get('volid') else None,
                        'format': r.get('format') or 'iso',
                        'size': r.get('size'),
                    } for r in rows
                ]
            })
        return out

    async def discover_ct_templates_by_node(self, nodes: list[str], storage_id: str = 'local'):
        out = []
        for node in nodes:
            rows = await self._get(f'/nodes/{node}/storage/{storage_id}/content', {'content': 'vztmpl'})
            out.append({
                'node': node,
                'storage_id': storage_id,
                'content_type': 'vztmpl',
                'items': [
                    {
                        'volid': r.get('volid'),
                        'filename': (r.get('volid') or '').split('/')[-1] if r.get('volid') else None,
                        'format': r.get('content') or 'vztmpl',
                        'size': r.get('size'),
                    } for r in rows
                ]
            })
        return out

    async def discover_vm_templates_by_node(self, nodes: list[str]):
        out = []
        for node in nodes:
            rows = await self._get(f'/nodes/{node}/qemu')
            out.append({
                'node': node,
                'templates': [
                    {'vmid': r.get('vmid'), 'name': r.get('name'), 'template': r.get('template'), 'status': r.get('status')}
                    for r in rows if r.get('template') in (1, True, '1')
                ]
            })
        return out

    async def download_url(self, target_node: str, storage_id: str, content: str, filename: str, source_url: str):
        return await self._post(f'/nodes/{target_node}/storage/{storage_id}/download-url', {
            'content': content,
            'filename': filename,
            'url': source_url,
        })

    async def task_status(self, node: str, upid: str):
        return await self._get(f'/nodes/{node}/tasks/{upid}/status')
