# Modernization Guardrails (19-41) Implementation Notes

Implemented foundations in code:
- Internal domain events (19)
- Initial policy layer extraction (28)
- Idempotency guard primitive (24)
- Concurrency lock primitive via idempotency reservation key (25)

Planned in next slices:
- Real-time event streaming (20)
- API v1/v2 router split and compatibility shims (21)
- OpenAPI-driven frontend contract generation (22)
- Explicit transaction wrapper utilities and retries/backoff (23, 32)
- State machine modules for VM/session/task (26)
- Secrets provider abstraction (27)
- Cache abstraction + metrics + feature flags + scheduler plugins (33-37)
- DR/export operational tooling and UX progressive disclosure hardening (38-41)
