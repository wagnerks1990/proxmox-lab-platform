# V2 rebuild roadmap

## Strategy

V2 is built alongside the alpha application. The alpha remains a reference and
migration source; it is not used as the architectural foundation. Proven code
is ported only after its behavior is covered by tests.

## Phase 0: containment and repository foundation

- fix canonical role resolution and fail-closed object scoping;
- enforce assigned and enabled templates at VM creation;
- disable false-success host bootstrap;
- correct clean-install configuration defects;
- restore a green backend suite;
- add CI and source-controlled wiki structure;
- create the V2 architecture, security, AI, deployment, and migration decisions.

Exit criteria: current alpha no longer contains the known cross-user role path,
tests are green, and V2 work has enforceable repository rules.

## Phase 1: identity and organization foundation

- organization, membership, role, and capability models;
- canonical policy engine and ownership service;
- secure login, password change, reset, revocation, and rate limiting;
- structured audit events;
- administrative organization and user workflows;
- legacy user/role dry-run migration report.

Exit criteria: the automated matrix proves student, teacher, organization-admin,
and platform-admin isolation.

## Phase 2: Proxmox vertical slice

- cluster configuration and least-privilege token validation;
- typed Proxmox adapter and deterministic fake server;
- inventory import and managed-resource tags;
- durable job and worker framework;
- atomic VMID allocation and idempotency;
- clone, observe, start, stop, reset, and verified delete;
- orphan discovery and non-destructive reconciliation.

Exit criteria: a restart at every operation state cannot duplicate or lose a VM,
and an end-to-end test completes the lifecycle against the lab cluster.

## Phase 3: classroom vertical slice

- class, enrollment, lab blueprint, lab run, and assignment models;
- teacher-scoped class and roster management;
- CSV import and optional join codes;
- student active-lab and assigned-resource views;
- quotas, schedules, access flags, and expiration;
- bulk provision, start, stop, extend, reset, and end-lab actions.

Exit criteria: one teacher can conduct a complete lab while another teacher and
all students remain correctly isolated.

## Phase 4: console and sessions

- Compose-managed Guacamole and guacd;
- short-lived server-side launch grants;
- RDP, SSH, and VNC policy enforcement;
- session heartbeat, disconnect, expiry, and reconnect;
- per-assignment credentials;
- session activity and troubleshooting views.

Exit criteria: supported browsers launch and reconnect without exposing control-
plane or reusable guest credentials.

## Phase 5: networking, pools, and cleanup

- multi-VM lab blueprints and private network segments;
- VLAN/SDN-aware placement;
- team assignments;
- persistent and nonpersistent pools;
- prewarming, checkout, release, and recycling;
- snapshot, revert, rebuild, TTL, and cleanup;
- capacity reservations and desired-state reconciliation.

Exit criteria: repeated class cycles leave no unowned resources and remain
within configured capacity and isolation policy.

## Phase 6: AI assistance

- optional provider gateway with local Ollama support;
- documentation retrieval;
- failure and health summaries;
- lab-blueprint drafting;
- capacity and remediation recommendations;
- redaction, budgets, prompt-injection controls, audit, and approval gates.

Exit criteria: AI can be disabled with no loss of core functionality, and no AI
path can bypass normal authorization or durable job execution.

## Phase 7: release engineering

- complete Docker Compose installer;
- first-run wizard;
- backup and tested restore;
- signed/versioned images and release manifests;
- controlled GUI update with compatibility checks;
- rollback or restore workflow;
- observability, retention, alerts, and operational runbooks;
- pilot and production acceptance suites.

Exit criteria: a fresh dedicated host can install, upgrade, recover, and run a
classroom acceptance test using only published documentation.

## Definition of the first pilot

The first pilot is intentionally narrow:

1. one organization and one Proxmox cluster;
2. administrator imports one approved template;
3. teacher creates one class and lab;
4. roster is imported and each student receives one VM;
5. each student sees and launches only their VM;
6. teacher can monitor and reset the lab;
7. ending the lab performs verified cleanup;
8. backup, restore, audit, and upgrade procedures are tested.

Multi-cluster scheduling, advanced pools, multi-VM topologies, external identity,
and AI-executed changes follow only after this pilot is dependable.
