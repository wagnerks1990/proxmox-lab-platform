# Deployment guide moved

The supported LabGoblin appliance uses Docker Compose and the guarded update
agent. The former host-virtualenv/manual-nginx procedure on this page is retired.

- Use [Deployment](operations/deployment.md) for installation and configuration.
- Use [First run](operations/first-run.md) for initial administrator enrollment.
- Use [Updates and rollback](operations/updates.md) for deployed upgrades.
- Use [Pre-production acceptance](operations/preproduction-acceptance.md) before a classroom pilot.

Do not update a deployed appliance with a direct `git pull` or manual Alembic
downgrade. Those paths bypass the database backup, exact-commit verification,
health gate, and recovery workflow.
