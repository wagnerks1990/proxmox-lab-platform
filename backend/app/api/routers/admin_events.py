import asyncio
import json
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_user_from_token
from app.db.session import get_db
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
