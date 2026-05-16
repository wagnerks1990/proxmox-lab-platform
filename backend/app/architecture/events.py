from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


@dataclass(slots=True)
class DomainEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


EventHandler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._subscribers[event_name].append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._subscribers.get(event.name, []):
            handler(event)


bus = EventBus()

VM_STARTED = 'VM_STARTED'
VM_STOPPED = 'VM_STOPPED'
VM_REBOOTED = 'VM_REBOOTED'
VM_DELETED = 'VM_DELETED'
SESSION_CREATED = 'SESSION_CREATED'
TASK_FAILED = 'TASK_FAILED'
GUEST_AGENT_DISCOVERED = 'GUEST_AGENT_DISCOVERED'
VALIDATION_FAILED = 'VALIDATION_FAILED'
