from app.models.models import DesktopPool
from app.schemas.pool_plan import PoolPlanAction, PoolPlanResponse
from app.services.pool_service import PoolService


class PoolPlanningService:
    def build_plan(self, pool: DesktopPool) -> PoolPlanResponse:
        warnings = PoolService(None).validate_pool_config(pool.__dict__)
        desired = max(pool.desired_size or 0, 0)
        start = pool.vmid_start or 0
        end = pool.vmid_end or (start + max(desired - 1, 0))
        vmids = [i for i in range(start, end + 1)][:desired]
        naming = []
        pat = pool.naming_pattern or f"{pool.name}-{{index}}"
        for idx, vmid in enumerate(vmids, start=1):
            naming.append(pat.replace("{index}", str(idx)).replace("{vmid}", str(vmid)))
        actions = [
            PoolPlanAction(
                action="would_validate_template",
                detail="Template fields would be validated",
            ),
            PoolPlanAction(
                action="would_check_storage",
                detail="Storage target would be checked for availability assumptions",
            ),
            PoolPlanAction(
                action="would_check_bridge",
                detail="Bridge/network settings would be validated",
            ),
        ] + [
            PoolPlanAction(
                action="would_create_vm", detail=f"Would plan VMID {v} ({naming[i]})"
            )
            for i, v in enumerate(vmids)
        ]
        return PoolPlanResponse(
            pool_id=pool.id,
            desired_size=desired,
            vmid_preview=vmids,
            naming_preview=naming,
            warnings=warnings,
            estimated_actions=actions,
        )
