from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import asyncio
import asyncssh
import ssl
from urllib.parse import urlencode
import websockets

from app.core.config import settings
from app.api.deps import get_user_from_token
from app.models.models import User, StudentVM, AuditLog
from app.services.console_access import get_console_vm_for_user
from app.services.organization_access import resolve_organization_context
from app.services.proxmox import ProxmoxClient
from app.db.tx import safe_commit
from app.architecture.async_retry import async_retry_with_backoff
from app.services.session_service import SessionService


class ConsoleWsService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def discover_vm_ip(interfaces):
        for iface in interfaces:
            for addr in iface.get("ip-addresses", []):
                if addr.get("ip-address-type") == "ipv4" and not addr.get(
                    "ip-address", ""
                ).startswith("127."):
                    return addr.get("ip-address")
        return None

    async def _watch_session_access(
        self,
        websocket: WebSocket,
        service: SessionService,
        session_id: int,
        user: User,
        vm: StudentVM,
        operation: str,
        auth_token: str,
        organization_id: int,
    ) -> None:
        while True:
            await asyncio.sleep(30)
            self.db.expire_all()
            try:
                current_user = get_user_from_token(auth_token, self.db)
                if getattr(current_user, "force_password_change", False):
                    raise HTTPException(
                        status_code=403, detail="Password change required"
                    )
                organization = resolve_organization_context(
                    self.db, current_user, organization_id
                )
                get_console_vm_for_user(
                    self.db,
                    user=current_user,
                    vm_id=vm.id,
                    organization=organization,
                    operation=operation,
                )
            except HTTPException:
                await websocket.close(code=1008, reason="Console access revoked")
                return
            if not service.heartbeat(session_id):
                await websocket.close(code=1008, reason="Session expired")
                return

    async def ssh_ws(
        self,
        websocket: WebSocket,
        user: User,
        vm: StudentVM,
        *,
        auth_token: str,
        organization_id: int,
    ):
        proxmox = ProxmoxClient(cluster_id=vm.proxmox_cluster_id)
        host = vm.assigned_ip
        if not host:
            try:
                interfaces = await proxmox.get_guest_network(vm.proxmox_node, vm.vmid)
                host = self.discover_vm_ip(interfaces)
                if host:
                    vm.assigned_ip = host
                    safe_commit(self.db)
            except Exception:
                pass
        if not host:
            await websocket.accept()
            await websocket.send_text(
                "ERROR: No VM IP address found. Install/enable QEMU guest agent or manually set assigned_ip."
            )
            await websocket.close(code=1000)
            return

        username = (
            vm.ssh_username
            or settings.lab_vm_ssh_username
            or vm.default_username
            or "student"
        )
        port = vm.ssh_port or 22
        if (
            not settings.lab_vm_ssh_private_key_path
            or not settings.lab_vm_ssh_known_hosts
        ):
            await websocket.accept()
            await websocket.send_text(
                "ERROR: SSH requires LAB_VM_SSH_PRIVATE_KEY_PATH and LAB_VM_SSH_KNOWN_HOSTS."
            )
            await websocket.close(code=1000)
            return

        await websocket.accept()
        self.db.add(
            AuditLog(
                organization_id=vm.organization_id,
                actor_id=user.id,
                action="ssh_ws_launch",
                target_type="student_vm",
                target_id=str(vm.vmid),
            )
        )
        safe_commit(self.db)
        svc = SessionService(self.db)
        launch = svc.create_launch(user, vm, "SSH_WS", "success", host)
        session = svc.create_launching_session(
            user, vm, "SSH_WS", connection_launch_id=launch.id
        )
        safe_commit(self.db)
        svc.mark_active(session.id)
        svc.heartbeat(session.id)

        try:
            async with asyncssh.connect(
                host,
                port=port,
                username=username,
                client_keys=[settings.lab_vm_ssh_private_key_path],
                known_hosts=settings.lab_vm_ssh_known_hosts,
            ) as conn:
                process = await conn.create_process(
                    term_type="xterm", term_size=(24, 120)
                )

                async def to_ws():
                    while not process.stdout.at_eof():
                        chunk = await process.stdout.read(1024)
                        if not chunk:
                            break
                        await websocket.send_text(chunk)

                async def from_ws():
                    while True:
                        process.stdin.write(await websocket.receive_text())

                t1 = asyncio.create_task(to_ws())
                t2 = asyncio.create_task(from_ws())
                watchdog = asyncio.create_task(
                    self._watch_session_access(
                        websocket,
                        svc,
                        session.id,
                        user,
                        vm,
                        "terminal",
                        auth_token,
                        organization_id,
                    )
                )
                _done, pending = await asyncio.wait(
                    {t1, t2, watchdog}, return_when=asyncio.FIRST_COMPLETED
                )
                for t in pending:
                    t.cancel()
        except WebSocketDisconnect:
            svc.mark_disconnected(session.id)
            return
        except Exception:
            try:
                svc.mark_failed(session.id, "SSH connection failed")
            except Exception:
                pass
            await websocket.send_text("ERROR: SSH connection failed")
            await websocket.close(code=1011)
        finally:
            svc.mark_disconnected(session.id)

    async def novnc_ws(
        self,
        websocket: WebSocket,
        user: User,
        vm: StudentVM,
        *,
        auth_token: str,
        organization_id: int,
    ):
        proxmox = ProxmoxClient(cluster_id=vm.proxmox_cluster_id)
        if not vm.console_enabled:
            await websocket.close(code=1008, reason="Console disabled for VM")
            return

        async def _ticket():
            return await proxmox.get_novnc_ticket(vm.proxmox_node, vm.vmid)

        rr = await async_retry_with_backoff(_ticket, max_attempts=3)
        if not rr.ok:
            await websocket.close(code=1011, reason="Failed to get noVNC ticket")
            return
        ticket_data = rr.value
        port = ticket_data.get("port")
        ticket = ticket_data.get("ticket")
        if not port or not ticket:
            await websocket.close(code=1011, reason="Failed to get noVNC ticket")
            return
        await websocket.accept()
        self.db.add(
            AuditLog(
                organization_id=vm.organization_id,
                actor_id=user.id,
                action="novnc_ws_launch",
                target_type="student_vm",
                target_id=str(vm.vmid),
            )
        )
        safe_commit(self.db)
        svc = SessionService(self.db)
        launch = svc.create_launch(user, vm, "NOVNC_WS", "success", str(vm.vmid))
        session = svc.create_launching_session(
            user, vm, "NOVNC_WS", connection_launch_id=launch.id
        )
        safe_commit(self.db)
        svc.mark_active(session.id)
        svc.heartbeat(session.id)
        query = urlencode({"port": port, "vncticket": ticket})
        path = f"/api2/json/nodes/{vm.proxmox_node}/qemu/{vm.vmid}/vncwebsocket?{query}"
        base = proxmox.base_url.replace("/api2/json", "")
        ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + path
        ssl_context = None
        if ws_url.startswith("wss://"):
            ssl_context = ssl.create_default_context()
            if not proxmox.verify_ssl:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
        try:
            async with websockets.connect(ws_url, ssl=ssl_context) as pmx:

                async def c2p():
                    while True:
                        message = await websocket.receive()
                        if message.get("bytes") is not None:
                            await pmx.send(message["bytes"])
                        elif message.get("text") is not None:
                            await pmx.send(message["text"])

                async def p2c():
                    while True:
                        data = await pmx.recv()
                        if isinstance(data, str):
                            await websocket.send_text(data)
                        else:
                            await websocket.send_bytes(data)

                t1 = asyncio.create_task(c2p())
                t2 = asyncio.create_task(p2c())
                watchdog = asyncio.create_task(
                    self._watch_session_access(
                        websocket,
                        svc,
                        session.id,
                        user,
                        vm,
                        "console",
                        auth_token,
                        organization_id,
                    )
                )
                _done, pending = await asyncio.wait(
                    {t1, t2, watchdog}, return_when=asyncio.FIRST_COMPLETED
                )
                for t in pending:
                    t.cancel()
        except WebSocketDisconnect:
            svc.mark_disconnected(session.id)
            return
        except Exception:
            try:
                svc.mark_failed(session.id, "noVNC proxy failed")
            except Exception:
                pass
            try:
                await websocket.send_text("ERROR: noVNC proxy failed")
                await websocket.close(code=1011)
            except Exception:
                return
        finally:
            svc.mark_disconnected(session.id)
