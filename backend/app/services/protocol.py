from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import StudentVM, User, ConnectionLaunch, AuditLog
from app.services.proxmox import ProxmoxClient


class ProtocolService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def discover_ip(interfaces: list[dict]) -> str | None:
        for iface in interfaces:
            for addr in iface.get("ip-addresses", []):
                ip = addr.get("ip-address", "")
                if addr.get("ip-address-type") == "ipv4" and not ip.startswith("127."):
                    return ip
        return None

    def log_launch(
        self,
        user: User,
        vm: StudentVM,
        protocol: str,
        status: str = "success",
        details: str | None = None,
    ):
        self.db.add(
            ConnectionLaunch(
                actor_id=user.id,
                vm_id=vm.id,
                protocol=protocol,
                status=status,
                details=details,
            )
        )

    async def web_terminal_url(self, user: User, vm: StudentVM) -> dict:
        if not vm.ssh_enabled:
            self.log_launch(user, vm, "WEB_TERMINAL", "failed", "web terminal disabled")
            self.db.commit()
            raise HTTPException(
                status_code=400,
                detail={"error": "WEB TERMINAL is not enabled for this VM."},
            )

        effective_ip = vm.assigned_ip
        if not effective_ip:
            interfaces = await ProxmoxClient(vm.proxmox_cluster_id).get_guest_network(
                vm.proxmox_node, vm.vmid
            )
            effective_ip = self.discover_ip(interfaces)
            if effective_ip:
                vm.assigned_ip = effective_ip
                self.db.flush()

        if not effective_ip:
            self.log_launch(
                user,
                vm,
                "WEB_TERMINAL",
                "failed",
                "No IP found. Enable QEMU Guest Agent or set assigned_ip.",
            )
            self.db.commit()
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No IP found. Enable QEMU Guest Agent or set assigned_ip."
                },
            )

        url = f"http://10.0.16.162:7681/?arg={effective_ip}"
        self.db.add(
            AuditLog(
                organization_id=vm.organization_id,
                actor_id=user.id,
                action="console_web_terminal",
                target_type="student_vm",
                target_id=str(vm.vmid),
            )
        )
        self.log_launch(user, vm, "WEB_TERMINAL", "success", effective_ip)
        self.db.commit()
        return {"type": "web_terminal", "url": url}

    async def novnc_ticket_scaffold(self, user: User, vm: StudentVM) -> dict:
        if not vm.console_enabled:
            raise HTTPException(
                status_code=400, detail={"error": "Console is not enabled for this VM."}
            )
        ticket = await ProxmoxClient(vm.proxmox_cluster_id).get_novnc_ticket(
            vm.proxmox_node, vm.vmid
        )
        self.db.add(
            AuditLog(
                organization_id=vm.organization_id,
                actor_id=user.id,
                action="console_novnc_scaffold",
                target_type="student_vm",
                target_id=str(vm.vmid),
            )
        )
        self.log_launch(user, vm, "NOVNC", "pending", "Console proxy not yet enabled")
        self.db.commit()
        return {
            "type": "novnc",
            "ticket": ticket,
            "message": "Console proxy not yet enabled",
        }
