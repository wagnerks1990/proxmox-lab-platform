# Security policy

## Supported versions

No production version is currently supported. The repository is undergoing a
V2 security and architecture rebuild. The current alpha should be used only in
an isolated development environment.

## Reporting a vulnerability

Do not open a public issue containing credentials, student data, infrastructure
addresses, or reproduction details that could affect a deployed lab. Use the
repository owner's private GitHub security-reporting channel.

Include the affected version or commit, impact, prerequisites, reproduction
steps, and any temporary mitigation. Do not test against systems or accounts
without authorization.

## Security expectations

- Never commit credentials or exported production data.
- Never deploy the documented development users or passwords to production.
- Require TLS verification for Proxmox and public application traffic.
- Use a dedicated least-privilege Proxmox token.
- Treat guest VMs and student-controlled content as hostile.
- Report suspected cross-user access immediately and disable student access
  until scope is understood.

The current threat model is maintained in
[`docs/security/threat-model.md`](docs/security/threat-model.md).
