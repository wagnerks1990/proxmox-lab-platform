from sqlalchemy.orm import Session
from app.models.models import DesktopPool, StudentVM, VMSession
from app.architecture.state_machines import SessionState
from app.services.pool_service import PoolService


class ReconciliationPlanningService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self) -> dict:
        pools = self.db.query(DesktopPool).count()
        stale = self.db.query(VMSession).filter(VMSession.state == SessionState.EXPIRED.value).count()
        warnings = 0
        for p in self.db.query(DesktopPool).all():
            warnings += len(PoolService(self.db).validate_pool_config(p.__dict__))
        return {'pools_total': pools, 'stale_sessions': stale, 'warnings': warnings}

    def preview(self) -> dict:
        pools = self.db.query(DesktopPool).all()
        desired = sum(max(p.desired_size or 0, 0) for p in pools if p.enabled and not p.maintenance_mode)
        current = self.db.query(StudentVM).count()
        stopped = self.db.query(StudentVM).filter(StudentVM.status == 'stopped').count()
        stale = self.db.query(VMSession).filter(VMSession.state == SessionState.EXPIRED.value).count()
        invalid = 0
        warn = 0
        for p in pools:
            errs = PoolService(self.db).validate_pool_config(p.__dict__)
            if errs:
                invalid += 1
                warn += len(errs)
        return {
            'missing_desktops': max(desired - current, 0),
            'excess_desktops': max(current - desired, 0),
            'stopped_desktops': stopped,
            'unassigned_desktops': 0,
            'stale_sessions': stale,
            'invalid_pool_config': invalid,
            'validation_warnings': warn,
            'proposed_actions': ['would_validate', 'would_cleanup', 'would_wait_for_manual_review'],
        }
