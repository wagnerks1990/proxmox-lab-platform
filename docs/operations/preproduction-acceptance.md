# Pre-production acceptance

LabGoblin is a pre-production candidate only after every required gate below has
a dated result, tester, tested commit SHA, environment identifier, and retained
evidence. A merge or green unit-test workflow is not a substitute for these
environment-dependent checks.

## Release identity

- Record the exact commit SHA and container image identities.
- Confirm the checkout is clean and the configured update branch resolves to
  the tested SHA.
- Confirm the database Alembic revision equals the sole repository head.
- Confirm release notes describe migrations, configuration changes, security
  impact, rollback limits, and known exclusions.

## Automated gates

- Backend formatting, lint, import, Bandit, dependency audit, and test suite pass.
- Migrations upgrade a populated previous-version PostgreSQL fixture and Alembic
  reports no model/schema drift.
- Frontend tests, production build, and dependency audit pass.
- Responsive-shell, role-navigation, accessible-name, focus, live-region, and
  design-token regression contracts pass.
- Generated OpenAPI files have no drift and every routed frontend endpoint exists.
- MkDocs strict build, branding regression check, secret scan, and Compose
  configuration validation pass.
- Disposable HTTP live test passes from first enrollment through verified VM
  deletion using the simulator.

## Security and tenancy

- Two organizations, two instructors, and multiple students pass the complete
  REST, SSE, WebSocket, console, lifecycle, preview, and delete isolation matrix.
- Logout, password reset, account disablement, membership removal, role change,
  assignment closure, and token expiry terminate active and queued access.
- Cross-origin REST and WebSocket attempts fail without changing state.
- Proxmox, SSH, console, updater, database, and bootstrap secrets are absent from
  URLs, browser storage, responses, logs, diagnostics, backups, and screenshots.
- TLS is valid from each managed client; authentication cookies are Secure; HSTS
  is enabled only after HTTPS is confirmed end to end.
- When Cloudflare is enabled, the origin is loopback-bound, the Tunnel token is
  root-owned and restricted to the dedicated connector group, direct-origin
  bypass fails, unexpected Host values fail, and
  forwarded headers from every non-Tunnel path are ignored.
- Required Cloudflare Access denies missing, forged, expired, wrong-issuer, and
  wrong-audience assertions while an accepted identity still requires a valid
  LabGoblin session, organization membership, and role.
- A least-privilege Proxmox token passes the documented permission matrix with
  TLS verification enabled.

## Real infrastructure

- On an isolated Proxmox test cluster, clone/start/stop/reboot/delete completes
  for the approved pilot template and every returned UPID is persisted and
  verified.
- Failure injection after each durable-operation transition produces no duplicate
  VM, lost task, cross-tenant action, or false success.
- Reconciliation distinguishes absent VMs from authentication, TLS, timeout, and
  server failures; record cleanup requires a fresh verified absence.
- noVNC launch, resize, disconnect, expiry, revocation, and reconnect pass in
  every supported browser.
- SSH terminal remains disabled until per-assignment credentials and trusted
  destination binding pass the hostile-guest pivot test.
- SSE remains live through the deployed proxy without buffering and terminates
  promptly after authorization revocation.
- On the real Cloudflare route, API/authentication responses bypass cache,
  WebSocket upgrades succeed, SSE reconnects without buffering, WAF rules have
  no unresolved false positives, and shared-NAT classroom traffic remains usable
  under the configured rate limits.

## Interface acceptance

- Logged-out, student, instructor, tenant administrator/owner, and platform
  administrator workflows pass at 320 x 568, 390 x 844, 768 x 1024,
  1024 x 768, and 1440 x 900.
- The interface has no page-level horizontal overflow. Dense data scrolls only
  within a labeled region or changes to an adaptive presentation.
- Keyboard-only and 200% zoom checks pass for navigation, organization
  selection, every changed form, dialogs, tables, and destructive actions.
- Skip navigation, visible focus, active-route semantics, persistent labels,
  heading order, live feedback, and dialog focus restoration pass manual review.
- Loading, empty, partial-failure, unavailable, forbidden, queued, succeeded,
  and failed states are distinguishable without relying on color.
- Compact navigation closes by Escape, backdrop, and route selection, keeps
  focus within the drawer while open, and restores focus to its trigger.
- Sanitized screenshots of representative public, student, instructor, and
  platform-administrator views are retained with the acceptance record.

## Upgrade, recovery, and operations

- Fresh install and resume after injected failures are tested on every supported
  OS version.
- Update succeeds from the previous candidate; concurrent check/apply/rollback
  requests serialize; a failed migration and failed health gate recover safely.
- Rollback restores the exact prior application images and compatible database.
- Encrypted off-host backup covers PostgreSQL, configuration, encryption keys,
  TLS material, and required state with documented retention and access control.
- A clean isolated restore meets the recorded RPO/RTO and passes application,
  login, tenancy, audit, and VM-reconciliation checks.
- Disk, backup, worker, scheduler, updater, database, Redis, and Proxmox alerts
  reach the assigned operator; log and backup retention are bounded.
- Cloudflare Tunnel-token and Access service-token rotation, connector outage,
  local health access, intentional disable, and application rollback are tested
  without temporarily exposing the origin to the Internet.
- Do not count R2 toward backup acceptance until a complete client-side
  encrypted artifact and isolated restore test cover every required state item.

## Approval

The pilot owner and technical operator must review unresolved risks and sign the
acceptance record. Any failed required gate keeps the release in alpha status.
