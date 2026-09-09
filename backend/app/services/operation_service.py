from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    AuditLog,
    DurableOperation,
    LabAssignment,
    StudentVM,
    VMTemplate,
    VmidAllocator,
)
from app.services.proxmox import ProxmoxClient
from app.architecture.events import DomainEvent, VM_STARTED, bus


def _is_not_found(exc: Exception) -> bool:
    response = getattr(exc, "response", None)
    return getattr(response, "status_code", None) == 404


def utcnow() -> datetime:
    return datetime.utcnow()


def allocate_vmid(db: Session, scope: str = "proxmox-cluster") -> int:
    allocator = (
        db.query(VmidAllocator)
        .filter(VmidAllocator.scope == scope)
        .with_for_update()
        .first()
    )
    if not allocator:
        allocator = VmidAllocator(scope=scope, next_value=200000)
        db.add(allocator)
        db.flush()
    largest = (
        db.query(StudentVM.vmid).order_by(StudentVM.vmid.desc()).limit(1).scalar()
        or 199999
    )
    value = max(allocator.next_value, largest + 1, 200000)
    allocator.next_value = value + 1
    allocator.updated_at = utcnow()
    return value


def safe_vm_name(username: str, lab_name: str, vmid: int) -> str:
    stem = re.sub(r"[^a-z0-9-]+", "-", f"{username}-{lab_name}".lower()).strip("-")[:45]
    return f"{stem or 'lab'}-{vmid}"


def enqueue_operation(
    db: Session,
    *,
    organization_id: int | None,
    requested_by: int | None,
    operation_type: str,
    target_type: str,
    target_id: str | None,
    payload: dict,
    idempotency_key: str | None = None,
) -> DurableOperation:
    key = idempotency_key or str(uuid.uuid4())
    existing = (
        db.query(DurableOperation)
        .filter(DurableOperation.idempotency_key == key)
        .first()
    )
    if existing:
        return existing
    row = DurableOperation(
        organization_id=organization_id,
        requested_by=requested_by,
        operation_type=operation_type,
        target_type=target_type,
        target_id=target_id,
        idempotency_key=key,
        payload_json=json.dumps(payload, sort_keys=True),
        state="queued",
        run_after=utcnow(),
    )
    db.add(row)
    db.flush()
    return row


def claim_operation(db: Session, worker_id: str) -> DurableOperation | None:
    now = utcnow()
    row = (
        db.query(DurableOperation)
        .filter(
            or_(
                DurableOperation.state == "queued",
                (DurableOperation.state == "running")
                & (DurableOperation.lease_expires_at < now),
            ),
            or_(
                DurableOperation.run_after.is_(None), DurableOperation.run_after <= now
            ),
        )
        .order_by(DurableOperation.created_at, DurableOperation.id)
        .with_for_update(skip_locked=True)
        .first()
    )
    if not row:
        return None
    row.state = "running"
    row.lease_owner = worker_id
    row.lease_expires_at = now + timedelta(seconds=settings.operation_lease_seconds)
    row.started_at = row.started_at or now
    row.attempts += 1
    db.commit()
    db.refresh(row)
    return row


async def execute_operation(db: Session, row: DurableOperation) -> None:
    payload = json.loads(row.payload_json or "{}")

    def renew_lease() -> None:
        row.lease_expires_at = utcnow() + timedelta(
            seconds=settings.operation_lease_seconds
        )
        db.commit()

    async def wait_for_task(proxmox: ProxmoxClient, node: str, upid: str) -> None:
        await proxmox.wait_for_task(node, upid, on_poll=renew_lease)

    def persist_task(upid: object, phase: str | None = None) -> str | None:
        row.proxmox_upid = str(upid or "") or None
        if phase:
            payload["_phase"] = phase
            row.payload_json = json.dumps(payload, sort_keys=True)
        renew_lease()
        return row.proxmox_upid

    if row.operation_type == "vm.create":
        vm = db.query(StudentVM).filter(StudentVM.id == int(row.target_id)).first()
        if not vm:
            raise RuntimeError("VM record no longer exists")
        template = db.query(VMTemplate).filter(VMTemplate.id == vm.template_id).first()
        if not template:
            raise RuntimeError("VM template no longer exists")
        proxmox = ProxmoxClient(vm.proxmox_cluster_id)
        if row.proxmox_upid:
            await wait_for_task(proxmox, vm.proxmox_node, row.proxmox_upid)
            live = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
        else:
            try:
                await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
                raise RuntimeError(
                    f"VMID {vm.vmid} already exists in Proxmox and is not owned by this operation"
                )
            except Exception as exc:
                if not _is_not_found(exc):
                    raise
            response = await proxmox.clone_vm(
                vm.proxmox_node, template.source_vmid, vm.vmid, vm.vm_name
            )
            persist_task(response.get("data"))
            if not row.proxmox_upid:
                raise RuntimeError("Proxmox clone did not return a task identifier")
            await wait_for_task(proxmox, vm.proxmox_node, row.proxmox_upid)
            live = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
        vm.status = live.get("status", "stopped")
        if payload.get("auto_start") and vm.status != "running":
            response = await proxmox.start_vm(vm.proxmox_node, vm.vmid)
            start_upid = response.get("data") if isinstance(response, dict) else None
            if start_upid:
                await wait_for_task(proxmox, vm.proxmox_node, str(start_upid))
            vm.status = (await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)).get(
                "status", "running"
            )
        assignment = (
            db.query(LabAssignment).filter(LabAssignment.student_vm_id == vm.id).first()
        )
        if assignment:
            assignment.status = "ready"
        result = {
            "vm_id": vm.id,
            "vmid": vm.vmid,
            "status": vm.status,
            "node": vm.proxmox_node,
        }
    elif row.operation_type in {"vm.start", "vm.stop", "vm.reboot"}:
        vm = db.query(StudentVM).filter(StudentVM.id == int(row.target_id)).first()
        if not vm:
            raise RuntimeError("VM record no longer exists")
        proxmox = ProxmoxClient(vm.proxmox_cluster_id)
        action = row.operation_type.split(".")[1]
        if not row.proxmox_upid:
            response = await getattr(proxmox, f"{action}_vm")(vm.proxmox_node, vm.vmid)
            persist_task(response.get("data") if isinstance(response, dict) else None)
        if row.proxmox_upid:
            await wait_for_task(proxmox, vm.proxmox_node, row.proxmox_upid)
        vm.status = (await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)).get(
            "status", vm.status
        )
        result = {"vm_id": vm.id, "vmid": vm.vmid, "status": vm.status}
    elif row.operation_type == "vm.delete":
        vm = db.query(StudentVM).filter(StudentVM.id == int(row.target_id)).first()
        if not vm:
            result = {"deleted": True, "already_absent": True}
        else:
            proxmox = ProxmoxClient(vm.proxmox_cluster_id)
            try:
                phase = payload.get("_phase")
                if phase in {"stop_submitted", "delete_submitted"} and row.proxmox_upid:
                    await wait_for_task(proxmox, vm.proxmox_node, row.proxmox_upid)
                    if phase == "stop_submitted":
                        row.proxmox_upid = None
                        payload["_phase"] = "stopped"
                        row.payload_json = json.dumps(payload, sort_keys=True)
                        renew_lease()

                live = await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
                if (
                    live.get("status") == "running"
                    and payload.get("_phase") != "delete_submitted"
                ):
                    stop = await proxmox.stop_vm(vm.proxmox_node, vm.vmid)
                    stop_upid = stop.get("data") if isinstance(stop, dict) else None
                    if stop_upid:
                        persist_task(stop_upid, "stop_submitted")
                        await wait_for_task(proxmox, vm.proxmox_node, row.proxmox_upid)
                        row.proxmox_upid = None
                        payload["_phase"] = "stopped"
                        row.payload_json = json.dumps(payload, sort_keys=True)
                        renew_lease()
                if payload.get("_phase") != "delete_submitted":
                    response = await proxmox.delete_vm(vm.proxmox_node, vm.vmid)
                    persist_task(response.get("data"), "delete_submitted")
                    if not row.proxmox_upid:
                        raise RuntimeError(
                            "Proxmox delete did not return a task identifier"
                        )
                    await wait_for_task(proxmox, vm.proxmox_node, row.proxmox_upid)
                try:
                    await proxmox.get_vm_status(vm.proxmox_node, vm.vmid)
                    raise RuntimeError("Proxmox still reports the VM after deletion")
                except Exception as exc:
                    if not _is_not_found(exc):
                        raise
            except Exception as exc:
                if not _is_not_found(exc):
                    raise
            assignment = (
                db.query(LabAssignment)
                .filter(LabAssignment.student_vm_id == vm.id)
                .first()
            )
            if assignment:
                assignment.student_vm_id = None
                assignment.status = (
                    "expired" if payload.get("expiration_cleanup") else "assigned"
                )
            result = {"deleted": True, "vm_id": vm.id, "vmid": vm.vmid}
            vm.deleted_at = utcnow()
            vm.status = "deleted"
    else:
        raise RuntimeError(f"Unsupported operation type: {row.operation_type}")

    row.state = "succeeded"
    row.result_json = json.dumps(result, sort_keys=True)
    row.error = None
    row.finished_at = utcnow()
    row.lease_owner = None
    row.lease_expires_at = None
    db.add(
        AuditLog(
            organization_id=row.organization_id,
            actor_id=row.requested_by,
            action=row.operation_type,
            target_type=row.target_type,
            target_id=row.target_id or "",
            outcome="success",
        )
    )
    db.commit()
    if row.operation_type == "vm.start":
        bus.publish(
            DomainEvent(
                name=VM_STARTED,
                payload={
                    "organization_id": row.organization_id,
                    "vm_id": int(row.target_id),
                    "actor_id": row.requested_by,
                },
            )
        )


def fail_or_retry(db: Session, row: DurableOperation, exc: Exception) -> None:
    row.error = str(exc)[:2048]
    row.lease_owner = None
    row.lease_expires_at = None
    if row.attempts < settings.operation_max_attempts:
        row.state = "queued"
        row.run_after = utcnow() + timedelta(seconds=min(60, 2**row.attempts))
    else:
        row.state = "failed"
        row.finished_at = utcnow()
        vm = (
            db.query(StudentVM).filter(StudentVM.id == int(row.target_id)).first()
            if row.target_type == "student_vm" and row.target_id
            else None
        )
        if vm and row.operation_type == "vm.create":
            vm.status = "error"
    db.add(
        AuditLog(
            organization_id=row.organization_id,
            actor_id=row.requested_by,
            action=row.operation_type,
            target_type=row.target_type,
            target_id=row.target_id or "",
            outcome="failure",
            message=row.error,
        )
    )
    db.commit()
