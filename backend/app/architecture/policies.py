from app.models.models import User, StudentVM


class PolicyError(PermissionError):
    pass


def can_launch_vm(user: User, vm: StudentVM) -> None:
    if user.role.name in {'Teacher', 'Admin'}:
        return
    if vm.owner_id != user.id:
        raise PolicyError('Not allowed to launch this VM.')


def can_view_audit_logs(user: User) -> None:
    if user.role.name not in {'Teacher', 'Admin'}:
        raise PolicyError('Not allowed to view audit logs.')
