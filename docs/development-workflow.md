# Development Workflow

## Branch strategy
- `main` = production-ready.
- `develop` = integration/testing.
- `feature/*` = active development.

## Merge flow
- Feature PRs target `develop`.
- Release PRs merge `develop` -> `main`.

## Codex safety policy
- Do not run deployment scripts, Proxmox actions, or runtime integration tests in Codex.
- Use static validation only (compile/build checks).
