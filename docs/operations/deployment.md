# LabGoblin deployment design

## Target

The supported initial deployment target is a dedicated Ubuntu host using Docker Compose. Production installation will not require editing source files.

Use a dedicated Debian 12 or Ubuntu 24.04 VM on Proxmox VE when possible. Allocate at least 2 vCPU, 4 GiB RAM, 30 GiB storage, a static IP, DNS, and outbound HTTPS access to GitHub and container registries.

Direct installation on a Proxmox VE host is supported only for development. The installer stops when it detects `pveversion` unless `--allow-proxmox-host` is supplied. Docker can alter firewall and bridge rules, so this override is a real operational risk rather than a cosmetic warning.

## Clean-install filesystem and service layout

Fresh LabGoblin installations use:

- application checkout: `/opt/labgoblin/app`;
- persistent host state: `/var/lib/labgoblin`;
- updater runtime directory: `/run/labgoblin-updater`;
- updater service/group: `labgoblin-updater.service` / `labgoblin-updater`;
- updater executable: `/usr/local/lib/labgoblin-updater.py`;
- Compose project: `labgoblin`;
- default PostgreSQL database/user: `labgoblin`;
- canonical Git repository: `https://github.com/wagnerks1990/labgoblin.git`.

These are canonical LabGoblin identifiers. This development baseline does not preserve predecessor application-owned paths, service names, or repository URLs.

## Current one-command installer

On the target VM:

```bash
curl -fsSL https://raw.githubusercontent.com/wagnerks1990/labgoblin/main/deploy/install.sh | sudo sh
```

That exact command requires the repository to be public. For a private repository, configure a read-only GitHub deploy key, clone the repository, and run `sudo deploy/install.sh`. The deploy key must remain available to the root-owned updater for later fetches. Do not put a personal access token in `.env`, the database, a Compose file, or a command retained in shell history.

For a development branch or private fork, download the installer and pass `--repository` and `--branch`. Private repositories require Git credentials or a read-only deploy key configured on the host before cloning.

The installer validates the operating system, generates separate bootstrap secrets, starts the Compose stack, runs Alembic migrations, installs the root-owned update agent, and waits for `/api/ready`. An installation is not reported successful until the health gate passes.

Bootstrap secrets are stored in a root-readable `.env` file. Operational settings remain in PostgreSQL. Back up both the database and `.env`; losing the encryption key can make stored credentials unrecoverable.

The current Compose stack contains the web application, API service with embedded scheduler and leased durable workers, PostgreSQL, and Redis. Guacamole, a separately scaled worker service, TLS automation, and an AI gateway are planned components and are not silently installed by the current script.

## Configuration boundary

The minimum bootstrap environment contains database, encryption, updater, and initial-administrator secrets. Cluster, storage, network, template, console, policy, AI-provider, update-channel, and organization configuration is stored in the database and managed through the GUI.

Secrets remain encrypted at rest and are never exported through normal settings APIs. Changing the database encryption key is a deliberate rotation procedure, not a normal update.

## Installer contract

The installer will:

1. verify root access, a supported Debian/Ubuntu OS, and the Proxmox-host safety guard;
2. create protected random bootstrap secrets;
3. create LabGoblin-owned filesystem, service, and state locations;
4. clone the configured Git branch and build local images;
5. create persistent PostgreSQL and Redis volumes;
6. run Alembic migrations in the API entrypoint;
7. start API/scheduler, PostgreSQL, Redis, and web services;
8. create a one-time first-admin enrollment token;
9. wait for the readiness endpoint;
10. print the LabGoblin URL and bootstrap token to the root operator.

An install is unsuccessful if any required component is unhealthy.

## Upgrade and rollback

Administrators manage implemented updates under **System Updates**. Manual checks are read-only. Applying an update refuses a dirty checkout, resolves the target commit, creates a PostgreSQL custom-format backup under `/var/lib/labgoblin/backups`, rebuilds the Compose stack, and waits for the public health endpoint.

If build, migration, startup, or health verification fails, the updater checks out the previous commit and restores the pre-update database automatically. The manual rollback button performs the same application-and-database restore.

Automatic updates are disabled by default and additionally require host policy `UPDATER_ALLOW_AUTOMATIC=true`. The repository is pinned by host configuration and cannot be redirected from the GUI. Apply operations require the exact SHA returned by a check and verify that it is reachable from the configured branch. GitHub credentials are never stored in the application database.

Only one update operation can hold the host lock. The updater is reachable only through the `labgoblin-updater` group-restricted Unix socket and requires a separate authentication token. The Docker socket is not mounted into the web or API containers.

The current backup covers PostgreSQL. It does not include `.env`, key material, TLS configuration, or Proxmox VE resources. Optional commit verification is enabled with `UPDATER_REQUIRE_SIGNED_COMMITS=true` and requires host Git trust configuration. Release-note display, migration compatibility manifests, and non-destructive workflow probes remain release-engineering work.

## Backup requirements

- scheduled encrypted PostgreSQL backups;
- separate protection for the encryption key;
- retention policy and capacity alerts;
- restore into an isolated validation environment;
- periodic automated restore tests;
- documented recovery objectives;
- no dependence on an untested backup.

## Health model

- **Liveness** confirms that one process can respond and reveals no topology.
- **Readiness** confirms required database and queue dependencies.
- **Integration health** is authenticated and reports Proxmox VE, Guacamole, asset, worker, and AI-provider state.
- **Workflow probes** validate a safe, non-destructive path using a dedicated test resource.
