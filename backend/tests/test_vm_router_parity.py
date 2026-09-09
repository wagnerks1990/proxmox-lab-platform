from app.api.routers import vms


def test_vm_router_paths():
    paths = {r.path for r in vms.router.routes}
    assert "/vms" in paths
