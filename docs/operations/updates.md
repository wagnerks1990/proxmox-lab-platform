# Updates and rollback

The root-owned updater listens only on a group-restricted Unix socket and authenticates API requests with a separate updater token. The API container does not receive the Docker socket.

## Manual update

1. Select **System Updates → Check**. This fetches the configured branch and returns its exact commit SHA.
2. Review that commit and release notes.
3. Apply the checked SHA. The updater refuses symbolic or shortened apply targets, repositories other than the host allowlist, commits not reachable from the configured branch, and dirty deployment checkouts.
4. Poll status while the host operation is queued or running. The request returns before the API container is replaced.

Before checkout, the updater creates a PostgreSQL custom-format backup. It rebuilds the Compose stack and waits for readiness. Failure checks out the previous commit, restores the backup, and restarts the prior stack.

## Automatic updates

Automatic updates are disabled by both database settings and host policy. Set `UPDATER_ALLOW_AUTOMATIC=true` only after the lab has passed restore testing. `UPDATER_REQUIRE_SIGNED_COMMITS=true` additionally runs `git verify-commit`; the host must have the required trust material installed or updates will fail closed.

## Honest rollback boundary

Rollback restores PostgreSQL and the application checkout. It does not restore Proxmox VMs, external storage, TLS certificates, SSH keys, or the `.env` file. Back up those separately. Validate restore in an isolated environment before treating the button as a recovery guarantee.
