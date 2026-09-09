#!/usr/bin/env python3
import os

from app.db.session import SessionLocal
from app.models.models import User
from seed_dev_admin import main as seed_dev_admin_main


def main() -> int:
    print(
        "[WARNING] This will delete ALL users and recreate only the default development admin account."
    )
    if os.getenv("RESET_DEV_USERS_CONFIRM") != "YES":
        print("Refusing to continue. Set RESET_DEV_USERS_CONFIRM=YES to proceed.")
        return 1

    db = SessionLocal()
    try:
        deleted = db.query(User).delete()
        db.commit()
        print(f"Deleted users: {deleted}")
    finally:
        db.close()

    seed_dev_admin_main()
    print("Development users reset complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
