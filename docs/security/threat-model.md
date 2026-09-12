# Security model and threat assumptions

## Security objective

A student must never access, operate, observe, or consume credentials belonging
to another student, team, class, organization, or the underlying Proxmox
infrastructure.

## Trust boundaries

The system treats these as separate trust zones:

- public browser clients;
- optional Cloudflare DNS, edge security, Access, and Tunnel connector;
- authenticated students;
- authenticated teachers;
- organization administrators;
- platform administrators;
- API and worker services;
- Guacamole;
- Proxmox management interfaces;
- guest VMs, which are considered hostile;
- optional local or cloud AI providers.

Compromise of a guest VM must not expose credentials reusable against another
guest or the control plane.

## Authorization rules

- Missing, unknown, or conflicting roles are denied.
- Roles grant capabilities; ownership and organization scope restrict objects.
- `X-Organization-ID` selects context but never grants access; active membership
  is verified server-side before loading a tenant resource.
- Core resource queries include organization scope before ownership or role
  checks, preventing valid IDs from becoming cross-tenant object references.
- A platform administrator's cross-organization access is an explicit
  break-glass path, not an implicit membership.
- Teachers are scoped to assigned classes unless a separate permission grants broader access.
- Tenant permissions come from the active organization membership rather than
  the legacy global role label; global `Admin` remains the explicit platform
  break-glass exception.
- Students require an active enrollment and explicit assignment.
- Frontend visibility is never considered an authorization control.
- Cloudflare Access approval is pre-authentication only. It never grants a
  LabGoblin role, membership, organization, object, or durable-operation right.
- Console, lifecycle, reset, snapshot, and deletion paths repeat authorization at the backend boundary.
- Destructive bulk actions require a preview and explicit confirmation token.

## Credential rules

- Proxmox uses a dedicated least-privilege service identity.
- TLS verification is required outside explicitly labeled local development.
- Root credentials are never persisted.
- VM access uses per-assignment or short-lived credentials, never one shared password.
- Browser clients never receive Proxmox API credentials.
- Long-term JWTs, console tickets, reconnect grants, and provider keys must not
  be placed in query strings. Current SSE and WebSocket paths authenticate with
  the HttpOnly session cookie; future launch grants must remain short-lived,
  audience-bound, server-side validated, and absent from browser URLs.
- Access JWTs are bound to revocable database sessions and a per-user token
  version. Logout, password reset, username change, and account disablement
  invalidate affected sessions immediately.
- Accounts awaiting a forced password change cannot access non-identity APIs.
- Failed login counters are persistent and keyed by a hash of username plus
  source address; attempted passwords are never retained.
- Secrets are redacted from structured logs, job payloads, audit details, and AI prompts.
- The encryption key is backed up separately from, but consistently with, the database.
- A required Cloudflare Access assertion is cryptographically verified for
  signature, algorithm, issuer, application audience, and time validity before
  the normal LabGoblin session and authorization checks run.
- Tunnel, Access service-token, and Cloudflare API credentials never enter the
  browser, database, URLs, normal logs, exports, or support bundles.
- Cloudflare client-IP and protocol headers are currently ignored as identity
  and audit attributes. Any future use must be limited to the exclusive
  configured connector path and never serve as identity evidence.

## Required security tests

The release suite must prove that:

- each role is allowed only its documented endpoints;
- students cannot enumerate or address another student's objects;
- teachers cannot cross organization or unassigned-class boundaries;
- inactive users cannot log in or retain REST/WebSocket access;
- changing a role changes effective authority immediately;
- disabled or unassigned templates cannot be provisioned;
- student VM creation and subsequent access require active organization
  membership, enrollment, lab run, assignment, and ownership;
- console flags and lab policy are enforced server-side;
- duplicate requests cannot create duplicate VMs;
- SSRF validation blocks unapproved infrastructure and asset destinations;
- secrets do not appear in API responses, URLs, logs, exports, or AI requests.
- required Access rejects missing, forged, expired, wrong-issuer, and
  wrong-audience assertions without weakening LabGoblin session/RBAC checks;
- direct-origin requests cannot bypass the loopback-bound Tunnel deployment;
- edge cache, WAF, and rate-limit rules preserve login cookies, API behavior,
  SSE continuity, WebSocket upgrades, and shared-school-NAT usability.

## Destructive operations

Delete, reset, rollback, and bulk cleanup use four stages:

1. authorized request;
2. immutable preview of affected resources;
3. explicit confirmation bound to the preview;
4. durable execution followed by observed-state verification.

If verification fails, the job remains unresolved and visible. The platform
must not report success merely because a request was submitted.

## AI boundary

AI output is untrusted input. AI can summarize and propose, but it cannot bypass
RBAC, object scope, validation, rate limits, approval, durable jobs, or audit.
See [AI safety and integration](../ai/ai-safety.md).
