from __future__ import annotations

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import WorkerRun


class WorkerRunService:
    def __init__(self, db: Session):
        self.db = db

    def start(self, worker_name: str, request_id: str | None = None) -> WorkerRun:
        row = WorkerRun(worker_name=worker_name, status='running', request_id=request_id)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def finish(self, run_id: int, status: str, summary: dict | None = None, error: str | None = None) -> WorkerRun | None:
        row = self.db.query(WorkerRun).filter(WorkerRun.id == run_id).first()
        if not row:
            return None
        row.status = status
        finished_at = datetime.now(timezone.utc)
        row.finished_at = finished_at
        if row.started_at:
            started_at = row.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            row.duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        row.summary_json = json.dumps(summary or {})
        row.error = error
        self.db.commit(); self.db.refresh(row)
        return row

    def recent(self, limit: int = 100):
        return self.db.query(WorkerRun).order_by(WorkerRun.started_at.desc()).limit(limit).all()
