# Updates and rollback

The root-owned updater listens only on a group-restricted Unix socket and authenticates API requests with a separate updater token. The API container does not receive the Docker socket.

## Manual update

1. Select **System Updates → Check**. This fetches the configured branch and returns its exact commit SHA.
2. Review that commit and release notes.
3. Apply the checked SHA. The updater binds the request to the latest check and refuses stale checks, branch movement, symbolic or shortened targets, non-forward commits, repositories other than the host allowlist, and dirty deployment checkouts.
4. Poll status while the host operation is queued or running. The request returns before the API container is replaced.

The updater first builds the checked revision in an isolated Git worktree. Only after that succeeds does it stop the API and web writers and create an atomic PostgreSQL custom-format backup. It then switches the checkout, starts the stack, waits for readiness, and atomically stages the matching installed updater for the next service restart. Failure checks out the previous commit, recreates and restores the database, and restarts the prior stack.

Rollback uses the same ordering: prebuild the target, stop writers, preserve a reverse backup, recreate the database from the selected backup, and pass the readiness gate. Commands have bounded execution time. If the host restarts during an operation, the persisted operation is marked failed instead of remaining permanently busy; inspect the deployment and retry.

## Automatic updates

Automatic updates are disabled by both database settings and host policy. Set `UPDATER_ALLOW_AUTOMATIC=true` only after the lab has passed restore testing. `UPDATER_REQUIRE_SIGNED_COMMITS=true` additionally runs `git verify-commit`; the host must have the required trust material installed or updates will fail closed.

## Honest rollback boundary

Rollback restores PostgreSQL and the application checkout. It does not restore Proxmox VMs, external storage, TLS certificates, SSH keys, or the `.env` file. Back up those separately. Validate restore in an isolated environment before treating the button as a recovery guarantee.
