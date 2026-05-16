from fastapi import APIRouter
from app.api import routes_legacy
from app.api.routes import auth, vms, templates, resource_pools, desktop_pools, proxmox_admin, sessions, monitoring, users, settings, schema_health

api_router = APIRouter()
# Preserve all existing URL paths from legacy router while modular files are introduced.
api_router.include_router(routes_legacy.router)

# Modular routers are scaffolded and ready for endpoint migration.
for r in [auth.router, vms.router, templates.router, resource_pools.router, desktop_pools.router, proxmox_admin.router, sessions.router, monitoring.router, users.router, settings.router, schema_health.router]:
    api_router.include_router(r)
