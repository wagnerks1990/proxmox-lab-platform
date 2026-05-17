# Contributing

## Branching model
- `main`: stable production branch.
- `develop`: integration/testing branch.
- `feature/*`: scoped implementation branches.

## Codex workflow
1. Branch from `develop` into `feature/<short-topic>`.
2. Keep commits focused and reversible.
3. Run safe static checks only in Codex unless explicitly approved.
4. Open PR into `develop` for feature work.
5. Promote `develop` to `main` after validation in deployment environment.

## PR expectations
- Clear summary and risk notes.
- Migration notes if database is touched.
- Rollback plan for backend/frontend changes.
