from dataclasses import dataclass


@dataclass
class TelemetryMetrics:
    active_session_count: int = 0
    failed_session_count: int = 0
    reconnect_attempts: int = 0
    reconnect_failures: int = 0
    websocket_disconnects: int = 0
    stale_cleanup_count: int = 0
    launch_failures: int = 0


metrics = TelemetryMetrics()
