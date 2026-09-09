from sqlalchemy.orm import Session
from app.services.telemetry_service import TelemetryService
from app.services.worker_run_service import WorkerRunService
from app.services.validation_service import ValidationService


class TroubleshootingService:
    def __init__(self, db: Session):
        self.db = db

    def recent(self, limit: int = 50) -> list[dict]:
        issues = []
        for e in TelemetryService(self.db).recent_events(limit=limit):
            if e.severity in {"error", "critical", "warning"}:
                issues.append(
                    {
                        "title": e.event_type,
                        "category": "telemetry",
                        "subsystem": e.source,
                        "severity": e.severity,
                        "probable_cause": "Operational event indicates warning/failure.",
                        "suggested_fix": "Inspect logs and retry workflow.",
                        "related_request_id": e.request_id,
                        "related_session_id": e.session_id,
                        "timestamp": e.created_at,
                    }
                )
        for r in WorkerRunService(self.db).recent(limit):
            if r.status == "failed":
                issues.append(
                    {
                        "title": f"Worker failure: {r.worker_name}",
                        "category": "workers",
                        "subsystem": r.worker_name,
                        "severity": "error",
                        "probable_cause": r.error or "Background worker failed.",
                        "suggested_fix": "Review worker run summary and scheduler health.",
                        "related_request_id": r.request_id,
                        "related_session_id": None,
                        "timestamp": r.started_at,
                    }
                )
        for c in ValidationService(self.db).run_checks():
            if c["status"] == "fail":
                issues.append(
                    {
                        "title": f"Validation: {c['name']}",
                        "category": c.get("category", "validation"),
                        "subsystem": c.get("category", "validation"),
                        "severity": c["severity"],
                        "probable_cause": c["message"],
                        "suggested_fix": c["suggested_fix"],
                        "related_request_id": None,
                        "related_session_id": None,
                        "timestamp": None,
                    }
                )
        return issues[:limit]
