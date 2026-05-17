# Enterprise Architecture Guardrails (Phase Foundation)

This folder introduces foundational primitives for required modernization items:

- Internal domain event bus (`events.py`) for decoupled orchestration hooks.
- Centralized RBAC policy checks (`policies.py`) to reduce route-level duplication.
- Idempotency reservation primitive (`idempotency.py`) for launch/retry safety.

## Immediate Adoption Pattern

1. Validate policy (`can_launch_vm`, `can_view_audit_logs`).
2. Reserve idempotency key for critical actions.
3. Perform operation inside explicit transaction boundaries.
4. Publish domain event (`VM_STARTED`, `TASK_FAILED`, etc.).
5. Release reservation keys in finally blocks.

## Next Steps

- Replace in-memory idempotency with Redis-backed implementation.
- Add event listeners for metrics, notifications, and websocket broadcasting.
- Add state-machine enforcement for VM/session/task transitions.
- Introduce feature flags and cache abstraction modules in this package.
