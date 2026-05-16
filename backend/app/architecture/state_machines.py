from __future__ import annotations

from enum import StrEnum


class SessionState(StrEnum):
    LAUNCHING = 'launching'
    ACTIVE = 'active'
    DISCONNECTED = 'disconnected'
    RECONNECTING = 'reconnecting'
    EXPIRED = 'expired'
    FAILED = 'failed'


class VmLifecycleState(StrEnum):
    UNKNOWN = 'unknown'
    STOPPED = 'stopped'
    STARTING = 'starting'
    RUNNING = 'running'
    STOPPING = 'stopping'
    REBOOTING = 'rebooting'
    SUSPENDED = 'suspended'
    ERROR = 'error'


class TaskState(StrEnum):
    QUEUED = 'queued'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    CANCELED = 'canceled'
    TIMEOUT = 'timeout'


class ReconciliationState(StrEnum):
    IDLE = 'idle'
    SCANNING = 'scanning'
    DRIFT_DETECTED = 'drift_detected'
    REPAIRING = 'repairing'
    HEALTHY = 'healthy'
    FAILED = 'failed'


SESSION_TRANSITIONS = {
    SessionState.LAUNCHING: {SessionState.ACTIVE, SessionState.FAILED},
    SessionState.ACTIVE: {SessionState.DISCONNECTED, SessionState.EXPIRED},
    SessionState.DISCONNECTED: {SessionState.RECONNECTING, SessionState.EXPIRED},
    SessionState.RECONNECTING: {SessionState.ACTIVE, SessionState.FAILED},
    SessionState.EXPIRED: set(),
    SessionState.FAILED: set(),
}


def validate_transition(current_state: StrEnum, next_state: StrEnum, transition_map: dict[StrEnum, set[StrEnum]]) -> bool:
    return next_state in transition_map.get(current_state, set())
