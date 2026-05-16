from app.api.routers import workers, admin_troubleshooting


def test_imports():
    assert workers.router and admin_troubleshooting.router
