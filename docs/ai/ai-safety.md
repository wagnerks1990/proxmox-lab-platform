# AI integration and safety

## Goals

AI support is optional. The platform remains fully functional when AI is
disabled or unavailable.

Initial AI features are read-only:

- explain failed provisioning jobs;
- summarize cluster health and incidents;
- search version-matched documentation;
- recommend capacity and placement changes;
- draft lab blueprints from teacher requirements;
- propose troubleshooting and remediation plans.

## Provider architecture

The AI gateway presents one internal contract and supports provider adapters.
The initial targets are local Ollama and OpenAI-compatible APIs. Additional
cloud adapters can be enabled without placing provider logic throughout the
application.

Provider configuration includes:

- enabled state;
- endpoint and model;
- encrypted API credential reference;
- allowed organizations and roles;
- monthly request or cost budget;
- data-retention classification;
- health and latency state.

Local models are appropriate when student or infrastructure data must remain on
site. Cloud providers require an explicit data classification and redaction
policy.

## Guardrails

- AI never receives Proxmox tokens, root passwords, SSH keys, database URLs,
  console tickets, or raw authentication headers.
- Student identifiers are minimized or pseudonymized when unnecessary.
- Retrieved documentation and logs are treated as untrusted content.
- Tool calls use server-generated structured arguments, allowlists, and normal
  backend authorization.
- AI cannot directly call Proxmox.
- AI-generated changes begin as a diff or execution preview.
- A human must approve every infrastructure mutation.
- Approved actions become normal durable jobs and remain subject to policy.
- Prompts, model/version, redaction decisions, approvals, and resulting job IDs
  are auditable without storing hidden reasoning or secrets.
- Budget, timeout, and rate-limit failures fail safely without blocking core
  classroom operations.

## Coding-agent readiness

The repository supports safe automated contribution through:

- explicit `AGENTS.md` invariants;
- feature-local instructions where needed;
- small modules with declared ownership;
- generated OpenAPI clients;
- architecture decision records;
- deterministic fake Proxmox and AI providers;
- integration tests for security boundaries;
- a maintained roadmap linked to issues;
- CI-required documentation and migration validation.

Coding agents must not claim live infrastructure validation from mocked or
offline tests. Pull requests list exactly what was tested and what still
requires the dedicated lab environment.
