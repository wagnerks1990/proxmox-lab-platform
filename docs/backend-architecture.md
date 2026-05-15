# Backend Architecture

## Layering
- `api/`: HTTP/websocket routes and request validation.
- `services/`: domain logic boundaries.
- `models/`: SQLAlchemy ORM.
- `schemas/`: API contracts.

## Target service boundaries
- `auth`
- `vm`
- `proxmox`
- `protocol`
- `audit`
- `session`
- `pools/templates`

## Logging
Use structured logging helpers to standardize event fields across services.
