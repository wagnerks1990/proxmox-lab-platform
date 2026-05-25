import os
import sys
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.models import DesktopPool, VMTemplate


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def parse_int(value: str, env_name: str):
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        print(f"WARN: {env_name} must be an integer, got {value!r}; skipping related records.")
        return None


def seed_template(db: Session) -> None:
    template_name = env("DEV_TEMPLATE_NAME")
    template_vmid = parse_int(env("DEV_TEMPLATE_VMID"), "DEV_TEMPLATE_VMID")
    template_node = env("DEV_TEMPLATE_NODE")
    _template_os = env("DEV_TEMPLATE_OS", "Linux")

    if not template_name or template_vmid is None or not template_node:
        print("WARN: Skipping vm_templates seed (set DEV_TEMPLATE_NAME, DEV_TEMPLATE_VMID, DEV_TEMPLATE_NODE).")
        return

    row = db.query(VMTemplate).filter(VMTemplate.name == template_name).first()
    if row is None:
        row = VMTemplate(
            name=template_name,
            source_vmid=template_vmid,
            proxmox_node=template_node,
            enabled=True,
        )
        db.add(row)
        print(f"CREATED: vm_template {template_name!r}")
    else:
        row.source_vmid = template_vmid
        row.proxmox_node = template_node
        row.enabled = True
        print(f"UPDATED: vm_template {template_name!r}")


def seed_desktop_pool(db: Session) -> None:
    pool_name = env("DEV_DESKTOP_POOL_NAME")
    if not pool_name:
        print("WARN: Skipping desktop_pools seed (set DEV_DESKTOP_POOL_NAME).")
        return

    template_vmid = parse_int(env("DEV_TEMPLATE_VMID"), "DEV_TEMPLATE_VMID")
    template_node = env("DEV_TEMPLATE_NODE") or None

    row = db.query(DesktopPool).filter(DesktopPool.name == pool_name).first()
    if row is None:
        row = DesktopPool(
            name=pool_name,
            description="Development desktop pool",
            pool_type="linked_clone",
            template_vmid=template_vmid,
            template_node=template_node,
            default_protocol="guacamole",
            desired_size=0,
            maintenance_mode=False,
            enabled=True,
        )
        db.add(row)
        print(f"CREATED: desktop_pool {pool_name!r}")
    else:
        row.template_vmid = template_vmid
        row.template_node = template_node
        row.enabled = True
        print(f"UPDATED: desktop_pool {pool_name!r}")


def main() -> int:
    print("INFO: Optional dev lab seed started (no Proxmox API calls, no VM creation).")
    print(f"WARN: DEV_RESOURCE_POOL_NAME={env('DEV_RESOURCE_POOL_NAME')!r} provided; resource_pools model is not present in current ORM and is skipped.")

    db = SessionLocal()
    try:
        seed_template(db)
        seed_desktop_pool(db)
        db.commit()
        print("PASS: Dev lab seed completed.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"FAIL: Dev lab seed failed: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
