from app.telemetry.metrics import metrics


def as_dict() -> dict[str, int]:
    return {
        "active_session_count": metrics.active_session_count,
        "failed_session_count": metrics.failed_session_count,
        "reconnect_attempts": metrics.reconnect_attempts,
        "reconnect_failures": metrics.reconnect_failures,
        "websocket_disconnects": metrics.websocket_disconnects,
        "stale_cleanup_count": metrics.stale_cleanup_count,
        "launch_failures": metrics.launch_failures,
    }
