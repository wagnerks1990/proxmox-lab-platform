# Instructor workflow

The teaching workspace follows the classroom lifecycle rather than exposing
raw infrastructure controls.

1. Create or select a class.
2. Enroll active organization members as students.
3. Create a lab blueprint using an enabled pool and approved access policy.
4. Create and schedule or activate a lab run.
5. Create assignments for the active roster.
6. Monitor assignments, VMs, sessions, events, and durable operations.
7. End the run only after reviewing its destructive preview.

Bulk start, stop, and reboot requests create durable operations. A button click
means the request was queued, not that Proxmox already reached the requested
state. Review **Operations** for failures and verified completion.

Ending a run immediately closes student authorization and queues the documented
cleanup. Do not manually remove the application record as a substitute for
verified Proxmox deletion.

Instructors see only classes and resources allowed by the selected organization
and their instructor scope. Platform administration remains unavailable unless
the account separately has that role.
