from sqlalchemy import text
from sqlalchemy.orm import Session
from app.services.proxmox import ProxmoxClient


async def health_summary(db: Session):
    db_ok = True
    pmx_ok = True
    db_error = None
    pmx_error = None
    try:
        db.execute(text('SELECT 1'))
    except Exception as exc:
        db_ok = False
        db_error = str(exc)
    try:
        await ProxmoxClient().list_nodes()
    except Exception as exc:
        pmx_ok = False
        pmx_error = str(exc)
    return {'backend': 'ok', 'database': {'ok': db_ok, 'error': db_error}, 'proxmox': {'ok': pmx_ok, 'error': pmx_error}}
