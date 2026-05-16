import asyncio
import json
from app.architecture.events import bus
from app.db.session import SessionLocal
from app.telemetry.metrics import metrics
from app.services.telemetry_service import TelemetryService
from app.telemetry.event_stream import event_stream


def _inc(name: str):
    def handler(event):
        setattr(metrics, name, getattr(metrics, name) + 1)
        db = SessionLocal()
        try:
            sev = 'error' if 'FAIL' in event.name else ('warning' if 'VALIDATION' in event.name else 'info')
            row = TelemetryService(db).record_event(event_type=event.name, severity=sev, source='event_bus', metadata_json=json.dumps(event.payload or {}), user_id=(event.payload or {}).get('actor_id'), vm_id=(event.payload or {}).get('vm_id'), session_id=(event.payload or {}).get('session_id'))
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(event_stream.publish({'event': event.name, 'id': row.id, 'severity': row.severity, 'created_at': str(row.created_at)}))
            except RuntimeError:
                pass
        finally:
            db.close()
    return handler


def register_subscribers() -> None:
    bus.subscribe('SESSION_STARTED', _inc('active_session_count'))
    bus.subscribe('SESSION_FAILED', _inc('failed_session_count'))
    bus.subscribe('RECONNECT_ATTEMPT', _inc('reconnect_attempts'))
    bus.subscribe('RECONNECT_FAILURE', _inc('reconnect_failures'))
    bus.subscribe('WEBSOCKET_DISCONNECT', _inc('websocket_disconnects'))
    bus.subscribe('STALE_CLEANUP', _inc('stale_cleanup_count'))
    bus.subscribe('VALIDATION_FAILED', _inc('launch_failures'))
