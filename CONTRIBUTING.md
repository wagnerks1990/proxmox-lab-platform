# Contributing

## Branching model
- `main`: source-of-truth branch for the current alpha and release candidates.
- `feature/*`, `fix/*`, and `audit/*`: scoped implementation branches created from `main`.

LabGoblin does not currently maintain a `develop` branch. The repository is not
production-supported merely because a change has reached `main`; release status
is defined by `SECURITY.md`, the roadmap, and the pre-production acceptance
record.

## Codex workflow
1. Branch from the current `main` into a focused branch.
2. Keep commits focused and reversible.
3. Run the complete safe local validation suite described in
   `docs/development/validation.md`.
4. Open a pull request into `main`.
5. Do not describe a build as pilot-ready until the environment-dependent gates
   in `docs/operations/preproduction-acceptance.md` are recorded as passing.

## PR expectations
- Clear summary and risk notes.
- Migration notes if database is touched.
- Rollback plan for backend/frontend changes.
- Exact validation results and explicit validation gaps.
- Documentation updates for changed behavior or operations.
