from app.architecture.events import bus
from app.telemetry.metrics import metrics


def _inc(name: str):
    def handler(_event):
        setattr(metrics, name, getattr(metrics, name) + 1)
    return handler


def register_subscribers() -> None:
    bus.subscribe('SESSION_STARTED', _inc('active_session_count'))
    bus.subscribe('SESSION_FAILED', _inc('failed_session_count'))
    bus.subscribe('RECONNECT_ATTEMPT', _inc('reconnect_attempts'))
    bus.subscribe('RECONNECT_FAILURE', _inc('reconnect_failures'))
    bus.subscribe('WEBSOCKET_DISCONNECT', _inc('websocket_disconnects'))
    bus.subscribe('STALE_CLEANUP', _inc('stale_cleanup_count'))
    bus.subscribe('VALIDATION_FAILED', _inc('launch_failures'))
