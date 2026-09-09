from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.models import VMSession, TelemetryEvent, WorkerRun, DesktopPool
from app.architecture.state_machines import SessionState


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self) -> dict:
        s_state = dict(
            self.db.query(VMSession.state, func.count(VMSession.id))
            .group_by(VMSession.state)
            .all()
        )
        s_proto = dict(
            self.db.query(VMSession.protocol, func.count(VMSession.id))
            .group_by(VMSession.protocol)
            .all()
        )
        t_sev = dict(
            self.db.query(TelemetryEvent.severity, func.count(TelemetryEvent.id))
            .group_by(TelemetryEvent.severity)
            .all()
        )
        w_status = dict(
            self.db.query(WorkerRun.status, func.count(WorkerRun.id))
            .group_by(WorkerRun.status)
            .all()
        )
        p_type = dict(
            self.db.query(DesktopPool.pool_type, func.count(DesktopPool.id))
            .group_by(DesktopPool.pool_type)
            .all()
        )
        p_status = {
            "enabled": self.db.query(func.count(DesktopPool.id))
            .filter(DesktopPool.enabled.is_(True))
            .scalar()
            or 0,
            "maintenance": self.db.query(func.count(DesktopPool.id))
            .filter(DesktopPool.maintenance_mode.is_(True))
            .scalar()
            or 0,
        }
        launch_failures = int(t_sev.get("error", 0) + t_sev.get("critical", 0))
        reconnect_failures = int(
            self.db.query(func.count(TelemetryEvent.id))
            .filter(TelemetryEvent.event_type == "RECONNECT_FAILURE")
            .scalar()
            or 0
        )
        stale_sessions = int(
            self.db.query(func.count(VMSession.id))
            .filter(VMSession.state == SessionState.EXPIRED.value)
            .scalar()
            or 0
        )
        active_sessions = int(
            self.db.query(func.count(VMSession.id))
            .filter(VMSession.state == SessionState.ACTIVE.value)
            .scalar()
            or 0
        )
        recent_failure_count = int(
            self.db.query(func.count(WorkerRun.id))
            .filter(WorkerRun.status == "failed")
            .scalar()
            or 0
        )
        return {
            "sessions_by_state": {str(k): int(v) for k, v in s_state.items()},
            "sessions_by_protocol": {str(k): int(v) for k, v in s_proto.items()},
            "telemetry_by_severity": {str(k): int(v) for k, v in t_sev.items()},
            "worker_runs_by_status": {str(k): int(v) for k, v in w_status.items()},
            "pools_by_type": {str(k): int(v) for k, v in p_type.items()},
            "pools_by_status": {str(k): int(v) for k, v in p_status.items()},
            "launch_failures": launch_failures,
            "reconnect_failures": reconnect_failures,
            "stale_sessions": stale_sessions,
            "active_sessions": active_sessions,
            "recent_failure_count": recent_failure_count,
        }
