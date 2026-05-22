#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.models import Role, User


def main() -> int:
    username = os.getenv("DEV_ADMIN_USERNAME", "admin")
    email = os.getenv("DEV_ADMIN_EMAIL", "admin@example.local")
    password = os.getenv("DEV_ADMIN_PASSWORD")

    if not password:
        print("DEV_ADMIN_PASSWORD is required.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        role_names = ["Student", "Teacher", "Admin"]
        role_map: dict[str, Role] = {}
        for role_name in role_names:
            role = db.query(Role).filter(Role.name == role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.add(role)
                db.flush()
            role_map[role_name] = role

        admin_role = role_map["Admin"]

        user = db.query(User).filter(User.username == username).first()
        if user is None:
            user = db.query(User).filter(User.email == email).first()

        password_hash = get_password_hash(password)
        if user is None:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role_id=admin_role.id,
                role=admin_role.name,
                is_active=True,
                force_password_change=False,
            )
            db.add(user)
            action = "created"
        else:
            user.username = username
            user.email = email
            user.password_hash = password_hash
            user.role_id = admin_role.id
            user.role = admin_role.name
            user.is_active = True
            action = "updated"

        db.commit()
        print(f"Development admin {action}: username={username} email={email}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
