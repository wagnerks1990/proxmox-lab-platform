from sqlalchemy.orm import Session
from app.models.models import AuditLog


def recent_audit_logs(db: Session, limit: int = 200):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
