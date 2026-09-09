from app.api.routers import auth, classroom, health, templates, audit, vms


def test_router_imports():
    assert (
        auth.router
        and classroom.router
        and health.router
        and templates.router
        and audit.router
        and vms.router
    )
