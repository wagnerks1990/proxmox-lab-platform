from sqlalchemy.orm import Session


def safe_commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
