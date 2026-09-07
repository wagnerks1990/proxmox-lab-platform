from sqlalchemy.orm import Session
from app.models.models import AuditLog


def recent_audit_logs(db: Session, organization_id: int, limit: int = 200):
    return db.query(AuditLog).filter(AuditLog.organization_id == organization_id).order_by(AuditLog.created_at.desc()).limit(limit).all()
