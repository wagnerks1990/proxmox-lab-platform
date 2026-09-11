# Student workflow

## Open an assigned lab

1. Sign in and select your organization if prompted.
2. Open **Create VM** to see active assignments that permit provisioning.
3. Select the assignment and approved template, then submit once.
4. Open **Operations** or **My Lab VMs** to follow queued provisioning.
5. Wait for verified readiness before launching the console.

Only VMs connected to your active enrollment, assignment, lab run, and
ownership are available. A lab that has not started or has ended is an inactive
assignment, not a reason to bypass the schedule.

## Manage a VM

Use **My Lab VMs** to start, stop, reboot, refresh, or connect when the lab
policy allows it. Buttons disappear or become unavailable when the assignment
or VM state prohibits an action. The backend rechecks permission when the
request executes.

Deletion displays the exact VM preview before confirmation. A queued deletion
is not complete until LabGoblin verifies that the Proxmox resource is absent.

## Connection safety

The browser console uses a same-origin WebSocket. Proxmox tickets never appear
in the browser URL. SSH terminal access remains disabled unless the deployment
has completed its separate security prerequisites.
