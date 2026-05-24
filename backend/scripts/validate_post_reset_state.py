import sys
from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.models import Role, User

REQUIRED_ROLES = {"Student", "Teacher", "Admin"}
REQUIRED_TABLES = [
    "users",
    "roles",
    "vm_templates",
    "student_vms",
    "audit_logs",
    "vm_sessions",
    "connection_launches",
    "telemetry_events",
    "worker_runs",
    "desktop_pools",
]
# resource_pools is deprecated in this codebase; desktop_pools is the active pool model.
OPTIONAL_TABLES = []
WARN_IF_EMPTY = {"vm_templates", "student_vms", "desktop_pools"}


def log(status: str, msg: str) -> None:
    print(f"{status}: {msg}")


def main() -> int:
    failures = 0
    db = SessionLocal()
    try:
        present_roles = {r.name for r in db.query(Role).all()}
        missing = sorted(REQUIRED_ROLES - present_roles)
        if missing:
            log("FAIL", f"Missing required roles: {', '.join(missing)}")
            failures += 1
        else:
            log("PASS", "Required roles exist: Student, Teacher, Admin")

        admin_user = (
            db.query(User)
            .join(Role, User.role_id == Role.id)
            .filter(Role.name == "Admin", User.is_active.is_(True))
            .first()
        )
        if admin_user is None:
            log("FAIL", "No active admin user found")
            failures += 1
        else:
            log("PASS", f"Active admin user found: {admin_user.username}")
    finally:
        db.close()

    table_checks = [(name, True) for name in REQUIRED_TABLES] + [(name, False) for name in OPTIONAL_TABLES]
    for table, required in table_checks:
        table_db = SessionLocal()
        try:
            count = table_db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            if table in WARN_IF_EMPTY and count == 0:
                log("WARN", f"{table} is queryable but empty")
            else:
                log("PASS", f"{table} query ok (rows={count})")
        except Exception as exc:
            table_db.rollback()
            if required:
                log("FAIL", f"Missing required table or query failure for {table}: {exc}")
                failures += 1
            else:
                log("WARN", f"Optional table {table} missing or not queryable: {exc}")
        finally:
            table_db.close()

    log("PASS", "Alembic head/current checks remain covered by scripts/validate_deploy.py")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
