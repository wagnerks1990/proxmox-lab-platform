# Disposable live test

The live-test harness provides a repeatable HTTP-level test of the application
without requiring a Proxmox server. It starts the normal PostgreSQL, Redis,
backend, and frontend services plus a small stateful Proxmox API simulator.

## Safety boundary

The workflow creates users, classroom records, and VM records, then tombstones
the VM record and deletes the simulated VM. Run it only against the disposable
Compose project and volumes.
The runner enforces both safeguards below:

- the target URL hostname must be `localhost`, `127.0.0.1`, or `::1`;
- `--i-understand-this-deletes-data` must be supplied.

Those checks reduce mistakes; they do not make a reused local database safe.
Always bring the stack down with `--volumes` before and after a fresh run.

## Run locally

Docker with the Compose plugin is required. From the repository root:

```bash
export POSTGRES_PASSWORD='live-test-database-password'
export JWT_SECRET_KEY='live-test-jwt-secret-at-least-32-characters'
export CONFIG_ENCRYPTION_KEY='live-test-encryption-key-at-least-32-characters'
export UPDATER_TOKEN='live-test-updater-token'
export BOOTSTRAP_ADMIN_TOKEN='live-test-bootstrap-token'
export UPDATER_GID='0'

docker compose -f docker-compose.yml -f docker-compose.live-test.yml down \
  --volumes --remove-orphans
docker compose -f docker-compose.yml -f docker-compose.live-test.yml up -d --build

until curl -fsS http://127.0.0.1:8080/api/ready; do sleep 2; done
python scripts/live_test.py \
  --base-url http://127.0.0.1:8080 \
  --bootstrap-token "$BOOTSTRAP_ADMIN_TOKEN" \
  --i-understand-this-deletes-data

docker compose -f docker-compose.yml -f docker-compose.live-test.yml down \
  --volumes --remove-orphans
```

The test fails unless `/api/ready` returns the JSON boolean `ready: true`. It
also treats unexpected HTTP errors, failed durable operations, and timeouts as
failures while accepting expected responses such as `204` logout and `404`
after verified deletion.

## Covered behavior

The script verifies:

1. readiness and one-time administrator enrollment;
2. organization selection and a manually supplied least-privilege token;
3. template, pool, class, enrollment, lab run, and assignment setup;
4. student login and assignment-bound provisioning;
5. durable clone, start, stop, and delete completion;
6. application-record tombstoning and hiding after the simulated VM disappears;
7. session logout.

## Troubleshooting

Inspect the complete Compose state and logs before cleanup:

```bash
docker compose -f docker-compose.yml -f docker-compose.live-test.yml ps
docker compose -f docker-compose.yml -f docker-compose.live-test.yml logs --no-color
```

Use a new volume set after any partial run. One-time bootstrap intentionally
fails against a database that already contains an administrator.

## Limits

This is an integration simulator, not a Proxmox conformance test. It does not
validate real API permissions, certificates, task timing, clusters, shared
storage, bridges/VLANs, guest agents, noVNC, Guacamole, nginx, systemd, or host
failure recovery. Those require an isolated real Proxmox test cluster and a
separate operator checklist before classroom use.
