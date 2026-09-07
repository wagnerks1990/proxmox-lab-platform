from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import asyncio
import asyncssh
import websockets

from app.core.config import settings
from app.models.models import User, StudentVM, AuditLog
from app.services.proxmox import ProxmoxClient
from app.db.tx import safe_commit
from app.architecture.async_retry import async_retry_with_backoff
from app.services.session_service import SessionService


class ConsoleWsService:
    def __init__(self, db: Session):
        self.db = db
        self.proxmox = ProxmoxClient()

    @staticmethod
    def discover_vm_ip(interfaces):
        for iface in interfaces:
            for addr in iface.get('ip-addresses', []):
                if addr.get('ip-address-type') == 'ipv4' and not addr.get('ip-address', '').startswith('127.'):
                    return addr.get('ip-address')
        return None

    async def ssh_ws(self, websocket: WebSocket, user: User, vm: StudentVM):
        host = vm.assigned_ip
        if not host:
            try:
                interfaces = await self.proxmox.get_guest_network(vm.proxmox_node, vm.vmid)
                host = self.discover_vm_ip(interfaces)
                if host:
                    vm.assigned_ip = host
                    safe_commit(self.db)
            except Exception:
                pass
        if not host:
            await websocket.accept(); await websocket.send_text('ERROR: No VM IP address found. Install/enable QEMU guest agent or manually set assigned_ip.'); await websocket.close(code=1000); return

        username = vm.ssh_username or settings.lab_vm_ssh_username or vm.default_username or 'student'
        password = settings.lab_vm_ssh_password
        port = vm.ssh_port or 22
        if not password:
            await websocket.accept(); await websocket.send_text('ERROR: LAB_VM_SSH_PASSWORD is not configured on backend.'); await websocket.close(code=1000); return

        await websocket.accept()
        self.db.add(AuditLog(organization_id=vm.organization_id, actor_id=user.id, action='ssh_ws_launch', target_type='student_vm', target_id=str(vm.vmid))); safe_commit(self.db)
        svc = SessionService(self.db)
        launch = svc.create_launch(user, vm, 'SSH_WS', 'success', host)
        session = svc.create_launching_session(user, vm, 'SSH_WS', connection_launch_id=launch.id)
        safe_commit(self.db)
        svc.mark_active(session.id)
        svc.heartbeat(session.id)
        svc.heartbeat(session.id)

        try:
            async with asyncssh.connect(host, port=port, username=username, password=password, known_hosts=None) as conn:
                process = await conn.create_process(term_type='xterm', term_size=(24, 120))
                async def to_ws():
                    while not process.stdout.at_eof():
                        chunk = await process.stdout.read(1024)
                        if not chunk: break
                        await websocket.send_text(chunk)
                async def from_ws():
                    while True:
                        process.stdin.write(await websocket.receive_text())
                t1 = asyncio.create_task(to_ws()); t2 = asyncio.create_task(from_ws())
                done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
                for t in pending: t.cancel()
        except WebSocketDisconnect:
            svc.mark_disconnected(session.id)
            return
        except Exception as exc:
            try:
                svc.mark_failed(session.id, str(exc))
            except Exception:
                pass
            await websocket.send_text(f'ERROR: SSH connection failed: {exc}'); await websocket.close(code=1011)

    async def novnc_ws(self, websocket: WebSocket, user: User, vm: StudentVM):
        if not vm.console_enabled:
            await websocket.close(code=1008, reason='Console disabled for VM'); return
        async def _ticket():
            return await self.proxmox.get_novnc_ticket(vm.proxmox_node, vm.vmid)
        rr = await async_retry_with_backoff(_ticket, max_attempts=3)
        if not rr.ok:
            await websocket.close(code=1011, reason='Failed to get noVNC ticket'); return
        ticket_data = rr.value
        port = ticket_data.get('port'); ticket = ticket_data.get('ticket')
        if not port or not ticket:
            await websocket.close(code=1011, reason='Failed to get noVNC ticket'); return
        await websocket.accept()
        self.db.add(AuditLog(organization_id=vm.organization_id, actor_id=user.id, action='novnc_ws_launch', target_type='student_vm', target_id=str(vm.vmid))); safe_commit(self.db)
        svc = SessionService(self.db)
        launch = svc.create_launch(user, vm, 'NOVNC_WS', 'success', str(vm.vmid))
        session = svc.create_launching_session(user, vm, 'NOVNC_WS', connection_launch_id=launch.id)
        safe_commit(self.db)
        svc.mark_active(session.id)
        svc.heartbeat(session.id)
        path = f"/api2/json/nodes/{vm.proxmox_node}/qemu/{vm.vmid}/vncwebsocket?port={port}&vncticket={ticket}"
        base = settings.proxmox_base_url.replace('/api2/json', '')
        ws_url = base.replace('https://', 'wss://').replace('http://', 'ws://') + path
        try:
            async with websockets.connect(ws_url, ssl=settings.proxmox_verify_ssl) as pmx:
                async def c2p():
                    while True: await pmx.send(await websocket.receive_text())
                async def p2c():
                    while True:
                        data = await pmx.recv(); await websocket.send_text(data if isinstance(data, str) else data.decode('utf-8', 'ignore'))
                t1 = asyncio.create_task(c2p()); t2 = asyncio.create_task(p2c())
                done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)
                for t in pending: t.cancel()
        except WebSocketDisconnect:
            svc.mark_disconnected(session.id)
            return
        except Exception as exc:
            try:
                svc.mark_failed(session.id, str(exc))
            except Exception:
                pass
            try:
                await websocket.send_text(f'ERROR: noVNC proxy failed: {exc}')
                await websocket.close(code=1011)
            except Exception:
                return
