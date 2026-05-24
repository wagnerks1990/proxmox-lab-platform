import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_user_from_token, get_current_user
from app.db.session import get_db
from app.models.models import AuditLog, TelemetryEvent, WorkerRun
from app.services.rbac import get_role_name
from app.telemetry.event_stream import event_stream

router = APIRouter()


def _sse_pack(data: str) -> str:
    return f"data: {data}\n\n"


@router.get('/admin/events/stream')
async def events_stream(request: Request, db: Session = Depends(get_db)):
    auth = request.headers.get('authorization', '')
    token = None
    if auth.lower().startswith('bearer '):
        token = auth.split(' ', 1)[1].strip()
    elif request.query_params.get('token'):
        token = request.query_params.get('token')
    if not token:
        raise HTTPException(status_code=401, detail='Unauthorized')
    user = get_user_from_token(token, db)
    if get_role_name(user) not in {'Teacher', 'Admin'}:
        raise HTTPException(status_code=403, detail='Forbidden')

    async def gen():
        q = event_stream.subscribe()
        try:
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=10)
                    yield _sse_pack(json.dumps(evt))
                except asyncio.TimeoutError:
                    yield _sse_pack('{"type":"heartbeat","status":"ok"}')
        finally:
            event_stream.unsubscribe(q)

    headers = {
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
    }
    return StreamingResponse(gen(), media_type='text/event-stream', headers=headers)


@router.get('/admin/events')
def list_events(
    type: str | None = None,
    severity: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    role = get_role_name(_user)
    if role not in {'Teacher', 'Admin'}:
        raise HTTPException(status_code=403, detail='Forbidden')
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    items = []

    audit_q = db.query(AuditLog)
    if q:
        audit_q = audit_q.filter(or_(AuditLog.action.ilike(f'%{q}%'), AuditLog.target_type.ilike(f'%{q}%')))
    for a in audit_q.order_by(AuditLog.created_at.desc()).limit(limit).all():
        items.append({
            'id': f'audit-{a.id}',
            'time': (a.created_at or datetime.utcnow()).isoformat(),
            'type': 'system',
            'severity': 'info',
            'message': a.action,
            'progress': None,
            'node': None,
            'related_object': f'{a.target_type}:{a.target_id}',
            'status': 'ok',
            'source': 'audit_logs',
        })

    tel_q = db.query(TelemetryEvent)
    if q:
        tel_q = tel_q.filter(TelemetryEvent.event_type.ilike(f'%{q}%'))
    if severity:
        tel_q = tel_q.filter(TelemetryEvent.severity == severity)
    for t in tel_q.order_by(TelemetryEvent.created_at.desc()).limit(limit).all():
        items.append({
            'id': f'tel-{t.id}',
            'time': (t.created_at or datetime.utcnow()).isoformat(),
            'type': type or 'system',
            'severity': t.severity or 'info',
            'message': t.event_type,
            'progress': None,
            'node': None,
            'related_object': f'vm:{t.vm_id}' if t.vm_id else None,
            'status': 'ok',
            'source': 'telemetry_events',
        })

    wr_q = db.query(WorkerRun)
    for w in wr_q.order_by(WorkerRun.started_at.desc()).limit(limit).all():
        items.append({
            'id': f'wr-{w.id}',
            'time': (w.started_at or datetime.utcnow()).isoformat(),
            'type': 'task',
            'severity': 'task',
            'message': w.name,
            'progress': None,
            'node': None,
            'related_object': None,
            'status': w.status,
            'source': 'worker_runs',
        })

    items.sort(key=lambda x: x['time'], reverse=True)
    if type:
        items = [i for i in items if i['type'] == type]
    total = len(items)
    items = items[offset:offset + limit]
    return {'items': items, 'total': total, 'limit': limit, 'offset': offset}
