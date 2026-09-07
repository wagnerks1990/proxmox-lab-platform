import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, select

from app.api.deps import get_user_from_token, get_current_user
from app.db.session import get_db
from app.models.models import AuditLog, StudentVM, TelemetryEvent, WorkerRun
from app.services.organization_access import OrganizationContext, enforce_organization_role, require_organization_role, resolve_organization_context
from app.telemetry.event_stream import event_stream

router = APIRouter()


def _sse_pack(data: str) -> str:
    return f"data: {data}\n\n"


def safe_str(value, default=""):
    if value is None:
        return default
    try:
        text = str(value)
        return text if text else default
    except Exception:
        return default


def safe_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return datetime.utcnow().isoformat()


def safe_int(value):
    try:
        return int(value)
    except Exception:
        return None


def normalize_severity(value):
    v = safe_str(value, "info").lower()
    if v in {"info", "warning", "error", "task"}:
        return v
    if v in {"warn"}:
        return "warning"
    return "info"


def normalize_event_type(value):
    v = safe_str(value, "system").lower()
    if v in {"desktop", "template", "server", "user", "pool", "system", "task"}:
        return v
    return "system"


def first_present(obj, *field_names, default=None):
    for f in field_names:
        v = getattr(obj, f, None)
        if v not in (None, ""):
            return v
    return default


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
    requested = request.headers.get('x-organization-id') or request.query_params.get('organization_id')
    try:
        organization = resolve_organization_context(db, user, int(requested) if requested else None)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail='Invalid organization ID')
    enforce_organization_role(organization, 'instructor')

    async def gen():
        q = event_stream.subscribe()
        try:
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=10)
                    if safe_int(evt.get('organization_id')) != organization.id:
                        continue
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
    organization: OrganizationContext = Depends(require_organization_role('instructor')),
):
    enforce_organization_role(organization, 'instructor')
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    items = []

    try:
        audit_q = db.query(AuditLog).filter(AuditLog.organization_id == organization.id)
        if q:
            audit_q = audit_q.filter(or_(AuditLog.action.ilike(f'%{q}%'), AuditLog.target_type.ilike(f'%{q}%')))
        for a in audit_q.order_by(AuditLog.created_at.desc()).limit(limit).all():
            items.append({
                'id': f'audit-{safe_int(a.id) or "unknown"}',
                'time': safe_datetime(getattr(a, 'created_at', None)),
                'type': 'system',
                'severity': 'info',
                'message': safe_str(getattr(a, 'action', None), 'Audit event'),
                'progress': None,
                'node': None,
                'related_object': f'{safe_str(getattr(a, "target_type", None), "target")}:{safe_str(getattr(a, "target_id", None), "unknown")}',
                'status': 'ok',
                'source': 'audit_logs',
            })
    except Exception:
        pass

    try:
        organization_vm_ids = select(StudentVM.id).where(StudentVM.organization_id == organization.id)
        tel_q = db.query(TelemetryEvent).filter(or_(TelemetryEvent.vm_id.is_(None), TelemetryEvent.vm_id.in_(organization_vm_ids)))
        if q:
            tel_q = tel_q.filter(TelemetryEvent.event_type.ilike(f'%{q}%'))
        if severity:
            tel_q = tel_q.filter(TelemetryEvent.severity == severity)
        for t in tel_q.order_by(TelemetryEvent.created_at.desc()).limit(limit).all():
            items.append({
                'id': f'tel-{safe_int(t.id) or "unknown"}',
                'time': safe_datetime(getattr(t, 'created_at', None)),
                'type': normalize_event_type(type or 'system'),
                'severity': normalize_severity(getattr(t, 'severity', None)),
                'message': safe_str(getattr(t, 'event_type', None), 'Telemetry event'),
                'progress': None,
                'node': None,
                'related_object': f'vm:{safe_int(getattr(t, "vm_id", None))}' if getattr(t, 'vm_id', None) else None,
                'status': 'ok',
                'source': 'telemetry_events',
            })
    except Exception:
        pass

    try:
        wr_q = db.query(WorkerRun)
        if q:
            wr_q = wr_q.filter(or_(WorkerRun.worker_name.ilike(f'%{q}%'), WorkerRun.status.ilike(f'%{q}%')))
        for w in wr_q.order_by(WorkerRun.started_at.desc()).limit(limit).all():
            msg = first_present(w, 'worker_name', 'status', default=f'Worker run {safe_int(getattr(w, "id", None)) or "unknown"}')
            items.append({
                'id': f'wr-{safe_int(w.id) or "unknown"}',
                'time': safe_datetime(getattr(w, 'started_at', None)),
                'type': 'task',
                'severity': 'task' if normalize_severity(getattr(w, 'status', None)) == 'info' else normalize_severity(getattr(w, 'status', None)),
                'message': safe_str(msg, f'Worker run {safe_int(getattr(w, "id", None)) or "unknown"}'),
                'progress': None,
                'node': None,
                'related_object': safe_str(getattr(w, 'request_id', None), None),
                'status': safe_str(getattr(w, 'status', None), 'unknown'),
                'source': 'worker_runs',
            })
    except Exception:
        pass

    items.sort(key=lambda x: x['time'], reverse=True)
    if type:
        items = [i for i in items if i['type'] == type]
    total = len(items)
    items = items[offset:offset + limit]
    return {'items': items, 'total': total, 'limit': limit, 'offset': offset}
