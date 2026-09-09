from __future__ import annotations

from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import TelemetryEvent


class TelemetryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_event(
        self,
        *,
        event_type: str,
        severity: str = "info",
        source: str = "backend",
        user_id: int | None = None,
        vm_id: int | None = None,
        session_id: int | None = None,
        request_id: str | None = None,
        metadata_json: str | None = None,
    ) -> TelemetryEvent:
        row = TelemetryEvent(
            event_type=event_type,
            severity=severity,
            source=source,
            user_id=user_id,
            vm_id=vm_id,
            session_id=session_id,
            request_id=request_id,
            metadata_json=metadata_json,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def recent_events(
        self,
        *,
        event_type: str | None = None,
        severity: str | None = None,
        user_id: int | None = None,
        vm_id: int | None = None,
        session_id: int | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ):
        q = self.db.query(TelemetryEvent)
        if event_type:
            q = q.filter(TelemetryEvent.event_type == event_type)
        if severity:
            q = q.filter(TelemetryEvent.severity == severity)
        if user_id:
            q = q.filter(TelemetryEvent.user_id == user_id)
        if vm_id:
            q = q.filter(TelemetryEvent.vm_id == vm_id)
        if session_id:
            q = q.filter(TelemetryEvent.session_id == session_id)
        if since:
            q = q.filter(TelemetryEvent.created_at >= since)
        return q.order_by(TelemetryEvent.created_at.desc()).limit(min(limit, 500)).all()

    def summary_counts(self) -> dict[str, int]:
        total = self.db.query(func.count(TelemetryEvent.id)).scalar() or 0
        return {
            "total_events": int(total),
            "failures": self.failure_counts(),
            "session_events": self.session_event_counts(),
        }

    def failure_counts(self) -> int:
        return int(
            self.db.query(func.count(TelemetryEvent.id))
            .filter(TelemetryEvent.severity.in_(["error", "critical"]))
            .scalar()
            or 0
        )

    def session_event_counts(self) -> int:
        return int(
            self.db.query(func.count(TelemetryEvent.id))
            .filter(TelemetryEvent.session_id.isnot(None))
            .scalar()
            or 0
        )
