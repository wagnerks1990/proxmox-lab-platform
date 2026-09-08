# Durable operations

## State model

VM create, start, stop, reboot, and delete requests return HTTP `202`. The API commits a `durable_operations` row before an external mutation. A scheduler worker claims one eligible row with a database lease, records attempts and the Proxmox UPID, and marks it `succeeded` only after observing the result.

States are `queued`, `running`, `succeeded`, `failed`, and `cancelled`. An expired `running` lease is claimable after a process restart. Failed work retries with bounded backoff up to `OPERATION_MAX_ATTEMPTS`.

`GET /api/operations` lists visible operations and `GET /api/operations/{id}` returns one operation. Students see only their own requests; instructors and tenant administrators can inspect their selected organization.

## VM identity and deletion

VMIDs are allocated under a row lock in `vmid_allocators` and are also protected by `uq_student_vms_vmid`. Human-facing names include the requested lab name after normalization, but database IDs and VMIDs remain authoritative.

VM deletion is deliberately separate from application-record cleanup. The normal delete flow requires `GET /api/vms/{id}/delete-preview`, exact confirmation, stop-if-running, Proxmox deletion, absence verification, and only then database-record removal. The administrator-only app-record endpoint never claims to delete Proxmox resources.

## Classroom lifecycle

Instructors can queue start, stop, or reboot for every assigned VM in a run. Ending a run immediately expires authorization and queues verified cleanup. The cleanup worker also detects elapsed assignment expiration times and submits idempotent delete operations.

## Operational recovery

- Do not manually set a running operation to succeeded.
- Confirm the Proxmox UPID and observed VM state before retrying an uncertain mutation.
- A failed delete preserves the application record for investigation.
- If a VM was removed outside the platform, run reconciliation and use the explicitly named app-record cleanup only after verifying the orphan state.
