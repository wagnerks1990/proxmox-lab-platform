from app.services.rbac import ROLE_STUDENT, STAFF_ROLES, get_role_name
from app.models.models import User, StudentVM


class PolicyError(PermissionError):
    pass


def can_launch_vm(user: User, vm: StudentVM) -> None:
    role = get_role_name(user)
    if role in STAFF_ROLES:
        return
    if role != ROLE_STUDENT or vm.owner_id != user.id:
        raise PolicyError("Not allowed to launch this VM.")


def can_view_audit_logs(user: User) -> None:
    if get_role_name(user) not in {"Teacher", "Admin"}:
        raise PolicyError("Not allowed to view audit logs.")
