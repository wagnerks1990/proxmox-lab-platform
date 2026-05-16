import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.api.deps import require_role
from app.telemetry.event_stream import event_stream

router = APIRouter()


def _sse_pack(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@router.get('/admin/events/stream')
async def events_stream(_user=Depends(require_role('Teacher', 'Admin'))):
    async def gen():
        q = event_stream.subscribe()
        try:
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15)
                    yield _sse_pack(evt.get('event', 'event'), json.dumps(evt))
                except asyncio.TimeoutError:
                    yield ': heartbeat\n\n'
        finally:
            event_stream.unsubscribe(q)
    return StreamingResponse(gen(), media_type='text/event-stream')
