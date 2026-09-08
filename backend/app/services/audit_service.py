import json

from sqlalchemy.orm import Session
from app.models.models import AuditLog


def recent_audit_logs(db: Session, organization_id: int, limit: int = 200):
    return db.query(AuditLog).filter(AuditLog.organization_id == organization_id).order_by(AuditLog.created_at.desc()).limit(limit).all()


def record_audit_event(
    db: Session,
    *,
    action: str,
    target_type: str,
    target_id: str,
    actor_id: int | None = None,
    organization_id: int | None = None,
    outcome: str = 'success',
    message: str | None = None,
    request_id: str | None = None,
    source_ip: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    """Add a structured, secret-free audit event to the current transaction."""
    event = AuditLog(
        organization_id=organization_id,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        outcome=outcome,
        message=message,
        request_id=request_id,
        source_ip=source_ip,
        metadata_json=json.dumps(metadata, sort_keys=True) if metadata else None,
    )
    db.add(event)
    return event
