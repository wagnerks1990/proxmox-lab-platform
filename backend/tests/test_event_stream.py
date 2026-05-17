import asyncio
from app.telemetry.event_stream import event_stream


def test_event_stream_publish_subscribe():
    async def _run():
        q = event_stream.subscribe()
        await event_stream.publish({'event': 'X'})
        evt = await asyncio.wait_for(q.get(), timeout=1)
        event_stream.unsubscribe(q)
        return evt
    evt = asyncio.run(_run())
    assert evt['event'] == 'X'
