import os
import importlib
import bcrypt
from sqlalchemy.orm import Session

from app.models.models import Role, User


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def import_sessionlocal():
    candidates = [
        "app.core.database",
        "app.db.database",
        "app.db.session",
        "app.db",
        "app.database",
    ]

    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
            session_local = getattr(module, "SessionLocal", None)
            if session_local is not None:
                print(f"Using SessionLocal from {module_name}")
                return session_local
        except Exception:
            continue

    raise SystemExit(
        "Could not find SessionLocal. Run: grep -R \"SessionLocal\" -n app"
    )


def hash_password(password: str) -> str:
    # Compatible with bcrypt-based auth storage.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def main() -> None:
    username = require_env("DEV_ADMIN_USERNAME")
    email = require_env("DEV_ADMIN_EMAIL")
    password = require_env("DEV_ADMIN_PASSWORD")

    SessionLocal = import_sessionlocal()
    db: Session = SessionLocal()

    try:
        roles = {
            1: "Student",
            2: "Teacher",
            3: "Admin",
        }

        for role_id, role_name in roles.items():
            role = db.query(Role).filter(Role.id == role_id).first()
            if role is None:
                role = Role(id=role_id, name=role_name)
                db.add(role)
            else:
                role.name = role_name

        admin = db.query(User).filter(User.username == username).first()

        password_hash = hash_password(password)

        if admin is None:
            admin = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role_id=3,
            )
            db.add(admin)
        else:
            admin.email = email
            admin.password_hash = password_hash
            admin.role_id = 3

        if hasattr(admin, "role"):
            admin.role = "Admin"

        if hasattr(admin, "is_active"):
            admin.is_active = True

        db.commit()
        print(f"Admin user seeded/updated: {username}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
