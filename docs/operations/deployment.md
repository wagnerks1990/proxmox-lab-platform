# Deployment design

## Target

The supported initial deployment target is a dedicated Ubuntu host using Docker
Compose. Production installation will not require editing source files.

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
