import os
from sqlalchemy.orm import Session

from app.models.models import Role, User
from app.services.security import hash_password
from app.db.session import SessionLocal


def main() -> None:
    username = os.getenv("DEV_ADMIN_USERNAME", "admin")
    email = os.getenv("DEV_ADMIN_EMAIL", "admin@example.local")
    password = os.getenv("DEV_ADMIN_PASSWORD", "admin")

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
        if hasattr(admin, "force_password_change"):
            admin.force_password_change = False

        db.commit()
        print(f"Admin user seeded/updated: {username}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
