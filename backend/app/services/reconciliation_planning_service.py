from sqlalchemy.orm import Session
from app.models.models import DesktopPool, StudentVM, VMSession
from app.architecture.state_machines import SessionState
from app.services.pool_service import PoolService


class ReconciliationPlanningService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self, organization_id: int | None = None) -> dict:
        pool_query = self.db.query(DesktopPool)
        session_query = self.db.query(VMSession)
        if organization_id is not None:
            pool_query = pool_query.filter(
                DesktopPool.organization_id == organization_id
            )
            session_query = session_query.filter(
                VMSession.organization_id == organization_id
            )
        pools = pool_query.count()
        stale = session_query.filter(
            VMSession.state == SessionState.EXPIRED.value
        ).count()
        warnings = 0
        for p in pool_query.all():
            warnings += len(PoolService(self.db).validate_pool_config(p.__dict__))
        return {"pools_total": pools, "stale_sessions": stale, "warnings": warnings}

    def preview(self, organization_id: int | None = None) -> dict:
        pool_query = self.db.query(DesktopPool)
        vm_query = self.db.query(StudentVM)
        session_query = self.db.query(VMSession)
        if organization_id is not None:
            pool_query = pool_query.filter(
                DesktopPool.organization_id == organization_id
            )
            vm_query = vm_query.filter(StudentVM.organization_id == organization_id)
            session_query = session_query.filter(
                VMSession.organization_id == organization_id
            )
        pools = pool_query.all()
        desired = sum(
            max(p.desired_size or 0, 0)
            for p in pools
            if p.enabled and not p.maintenance_mode
        )
        current = vm_query.count()
        stopped = vm_query.filter(StudentVM.status == "stopped").count()
        stale = session_query.filter(
            VMSession.state == SessionState.EXPIRED.value
        ).count()
        invalid = 0
        warn = 0
        for p in pools:
            errs = PoolService(self.db).validate_pool_config(p.__dict__)
            if errs:
                invalid += 1
                warn += len(errs)
        return {
            "missing_desktops": max(desired - current, 0),
            "excess_desktops": max(current - desired, 0),
            "stopped_desktops": stopped,
            "unassigned_desktops": 0,
            "stale_sessions": stale,
            "invalid_pool_config": invalid,
            "validation_warnings": warn,
            "proposed_actions": [
                "would_validate",
                "would_cleanup",
                "would_wait_for_manual_review",
            ],
        }
