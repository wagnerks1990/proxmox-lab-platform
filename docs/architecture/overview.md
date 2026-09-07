# V2 architecture

## Design goals

V2 is a classroom orchestration system, not a thin collection of Proxmox API
buttons. The database records desired state, durable workers reconcile that
state with Proxmox, and the API exposes explicit, authorized workflows.

The primary design goals are:

- safe student and teacher isolation;
- recoverable infrastructure mutations;
- a complete class-to-lab-to-assignment workflow;
- one-command installation on a dedicated Ubuntu host;
- database-managed operational configuration;
- reliable browser access through Guacamole;
- optional, permission-aware AI assistance;
- maintainability by both people and coding agents.

## Runtime components

| Component | Responsibility |
|---|---|
| Web | React/TypeScript application and role-aware user experience |
| API | Authentication, policy, validation, query APIs, and job submission |
| Worker | Proxmox mutations, discovery, reconciliation, cleanup, and retries |
| Scheduler | Creates periodic reconciliation, expiration, and health jobs |
| PostgreSQL | Authoritative configuration, desired state, jobs, and audit history |
| Redis | Queue transport, distributed locks, rate limits, and short-lived events |
| Guacamole/guacd | Supported RDP, SSH, and VNC browser access |
| Reverse proxy | TLS termination and routing for web, API, WebSocket, and Guacamole traffic |
| Documentation | Version-matched MkDocs wiki |
| AI gateway | Optional provider abstraction with redaction, budgets, and audit controls |

The API and scheduler are separate processes. Running multiple API instances
must not create duplicate scheduled work.

## Domain boundaries

V2 uses feature modules rather than large global router files:

- identity and organizations;
- classes and enrollments;
- lab blueprints and lab runs;
- Proxmox clusters and inventory;
- templates and assets;
- VM assignments and instances;
- networking and isolation;
- console sessions;
- durable jobs and reconciliation;
- audit and telemetry;
- AI recommendations.

Each feature owns its API schemas, application service, persistence model,
authorization policies, and tests. Proxmox-specific code is behind an adapter
interface so tests can use a deterministic fake implementation.

## Desired-state workflow

Infrastructure operations follow this sequence:

1. Validate authentication, organization scope, policy, quota, and input.
2. Create a durable job with a unique idempotency key.
3. Commit the desired state and audit request in one transaction.
4. A worker claims the job with a distributed lock.
5. The worker submits a Proxmox task and stores its UPID immediately.
6. The worker polls or reconciles the result after restarts.
7. The final observed state and audit outcome are committed.
8. Failures enter a retry, compensation, or manual-review state.

API request processes never own long-running Proxmox work through an in-memory
task.

## Resource identity

Every managed Proxmox resource receives platform tags containing immutable
organization, lab-run, assignment, and VM-instance identifiers. Names are for
people; tags and database identifiers establish ownership.

Deleting an application record is never equivalent to deleting a Proxmox
resource. Both operations have separate names, permissions, previews, and audit
events.

## Lab model

A **Lab Blueprint** is reusable curriculum infrastructure. It can describe one
VM or a multi-VM topology with private networks, routers, firewalls, services,
and client systems.

A **Lab Run** is a scheduled use of that blueprint by a class. It creates
assignments for individual students or teams and applies quotas, network
isolation, access permissions, start/end times, and cleanup policy.

This split supports introductory single-VM labs immediately without blocking
future Network+, Security+, or penetration-testing topologies.
