import asyncio
import socket
import uuid

from app.db.session import SessionLocal
from app.services.operation_service import claim_operation, execute_operation, fail_or_retry


def run_once() -> dict[str, int]:
    db = SessionLocal()
    worker_id = f'{socket.gethostname()}:{uuid.uuid4().hex[:8]}'
    try:
        row = claim_operation(db, worker_id)
        if not row:
            return {'claimed': 0}
        try:
            asyncio.run(execute_operation(db, row))
            return {'claimed': 1, 'succeeded': 1}
        except Exception as exc:
            db.rollback()
            row = db.query(type(row)).filter(type(row).id == row.id).first()
            if row:
                fail_or_retry(db, row, exc)
            return {'claimed': 1, 'failed': 1}
    finally:
        db.close()
