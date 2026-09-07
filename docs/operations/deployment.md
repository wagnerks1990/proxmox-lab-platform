# Deployment design

## Target

The supported initial deployment target is a dedicated Ubuntu host using Docker
Compose. Production installation will not require editing source files.

Use a dedicated Debian 12 or Ubuntu 24.04 VM on Proxmox when possible. Allocate
at least 2 vCPU, 4 GiB RAM, 30 GiB storage, a static IP, DNS, and outbound HTTPS
access to GitHub and container registries.

Direct installation on a Proxmox host is supported only for development. The
installer stops when it detects `pveversion` unless
`--allow-proxmox-host` is supplied. Docker can alter firewall and bridge rules,
so this override is a real operational risk rather than a cosmetic warning.

## Current one-command installer

On the target VM:

```bash
curl -fsSL https://raw.githubusercontent.com/wagnerks1990/proxmox-lab-platform/main/deploy/install.sh | sudo sh
```

That exact command requires the repository to be public. While it is private,
configure a read-only GitHub deploy key, clone the repository, and run
`sudo deploy/install.sh`. The deploy key must remain available to the root-owned
updater for later fetches. Do not put a personal access token in `.env`, the
database, a Compose file, or a command that will be retained in shell history.

For a development branch or private fork, download the installer and pass
`--repository` and `--branch`. Private repositories require Git credentials or
a read-only deploy key configured on the host before cloning.

The current installer validates the operating system, generates separate
bootstrap secrets, starts the Compose stack, runs Alembic migrations, installs
the root-owned update agent, and waits for `/api/ready`. An installation is not
reported successful until the health gate passes.

Bootstrap secrets are stored in a root-readable `.env` file. Operational
settings remain in PostgreSQL. Back up both the database and the `.env` file;
losing the encryption key can make stored credentials unrecoverable.

The final stack contains:

- reverse proxy;
- web application;
- API service;
- worker service;
- scheduler service;
- PostgreSQL;
- Redis;
- Guacamole and guacd;
- version-matched documentation;
- optional AI gateway.

## Configuration boundary

The minimum bootstrap environment contains database, encryption, and initial
administrator secrets. Cluster, storage, network, template, console, policy,
branding, AI-provider, update-channel, and organization configuration is stored
in the database and managed through the GUI.

Secrets remain encrypted at rest and are never exported through normal settings
APIs. Changing the database encryption key is a deliberate rotation procedure,
not a normal update.

## Installer contract

The supported installer will:

1. verify Docker, Compose, CPU, memory, storage, ports, time, and DNS;
2. create protected random bootstrap secrets;
3. pull immutable, versioned images;
4. create persistent volumes and private networks;
5. start PostgreSQL and Redis and wait for readiness;
6. run Alembic migrations as a one-shot job;
7. start API, worker, scheduler, Guacamole, docs, and web services;
8. create a one-time first-admin enrollment link;
9. run a complete smoke test;
10. print the URL and backup location without printing secrets.

An install is unsuccessful if any required component is unhealthy.

## Upgrade and rollback

Administrators manage implemented updates under **System Updates**. Manual
checks are read-only. Applying an update refuses a dirty checkout, resolves the
target commit, creates a PostgreSQL custom-format backup, rebuilds the Compose
stack, and waits for the public health endpoint.

If build, migration, startup, or health verification fails, the updater checks
out the previous commit and restores the pre-update database automatically.
The manual rollback button performs the same application-and-database restore.

Automatic updates are disabled by default. They can be enabled with a branch,
channel, check interval, and UTC maintenance hour. The repository itself is
pinned by the host configuration and cannot be redirected from the GUI. GitHub
credentials are never stored in the application database.

Only one update operation can hold the host lock. The updater is reachable only
through a group-restricted Unix socket and requires a separate authentication
token. The Docker socket is not mounted into the web or API containers.

Before an upgrade, the controller records the current version and performs a
coordinated backup of PostgreSQL, the database encryption key reference,
application configuration, Compose metadata, and current immutable image
identifiers.

The upgrade process downloads the selected release, validates signatures,
checks migration compatibility, shows release notes, creates the backup, runs
migrations, starts the new stack, and performs health and workflow probes.

Automatic rollback is permitted only when the database migration is declared
backward-compatible. Otherwise the UI must explain that database restore is
required and request explicit approval. A rollback button must never imply that
all migrations are automatically reversible.

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
- **Integration health** is authenticated and reports Proxmox, Guacamole, asset,
  worker, and AI-provider state.
- **Workflow probes** validate a safe, non-destructive path using a dedicated
  test resource.
