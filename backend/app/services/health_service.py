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
        client = ProxmoxClient()
        nodes = await client.list_nodes()
    except Exception as exc:
        pmx_ok = False
        pmx_error = str(exc)
        client = None
        nodes = []
    return {
        'backend': 'ok',
        'database': {'ok': db_ok, 'error': db_error},
        'proxmox': {
            'ok': pmx_ok,
            'error': pmx_error,
            'config_source': getattr(client, 'config_source', 'not_configured'),
            'nodes_discovered_count': len(nodes),
            'credential_status': 'present' if pmx_ok or client else 'missing',
        },
    }
