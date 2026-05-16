import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.api.deps import require_role

router = APIRouter()


def _sse_pack(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


@router.get('/admin/events/stream')
async def events_stream(_user=Depends(require_role('Teacher', 'Admin'))):
    async def gen():
        while True:
            yield ': heartbeat\n\n'
            yield _sse_pack('lifecycle', '{"status":"alive"}')
            await asyncio.sleep(15)
    return StreamingResponse(gen(), media_type='text/event-stream')
