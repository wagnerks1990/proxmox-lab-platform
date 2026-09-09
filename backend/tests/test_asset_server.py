from app.services.asset_server_control import (
    AssetServerControl,
    HostRunnerNotConfiguredError,
)


class Obj:
    def __init__(self, **k):
        self.__dict__.update(k)


class Q:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *a, **k):
        return self

    def first(self):
        return self.rows[0] if self.rows else None


class DB:
    def __init__(self, m):
        self.m = m

    def query(self, model):
        return Q(self.m.get(model, []))


def mkdb(host_access_rows=None):
    from app.models.models import ProxmoxCluster, ProxmoxNode, ProxmoxHostAccess

    return DB(
        {
            ProxmoxCluster: [Obj(id=1, is_active=True)],
            ProxmoxNode: [Obj(cluster_id=1, node_name="pve-lab-01", status="online")],
            ProxmoxHostAccess: host_access_rows or [],
        }
    )


def test_kind_validation():
    s = AssetServerControl(mkdb())
    try:
        s.status("bad")
        assert False
    except ValueError:
        assert True


def test_action_rejects_when_runner_disabled(monkeypatch):
    from app.services import asset_server_control as m

    monkeypatch.setattr(m.settings, "host_runner_enabled", False)
    s = AssetServerControl(mkdb())
    try:
        s.action("install", "iso")
        assert False
    except HostRunnerNotConfiguredError as e:
        assert "Host runner is not configured" in str(e)


def test_action_rejects_without_host_access_row(monkeypatch):
    from app.services import asset_server_control as m

    monkeypatch.setattr(m.settings, "host_runner_enabled", True)
    s = AssetServerControl(mkdb(host_access_rows=[]))
    try:
        s.action("start", "iso")
        assert False
    except HostRunnerNotConfiguredError:
        assert True


def test_action_rejects_without_validated_status(monkeypatch):
    from app.services import asset_server_control as m

    monkeypatch.setattr(m.settings, "host_runner_enabled", True)
    s = AssetServerControl(
        mkdb(
            host_access_rows=[
                Obj(
                    cluster_id=1,
                    node_name="pve-lab-01",
                    status="not_configured",
                    encrypted_private_key="x",
                )
            ]
        )
    )
    try:
        s.action("start", "iso")
        assert False
    except HostRunnerNotConfiguredError:
        assert True


def test_action_rejects_without_key_material(monkeypatch):
    from app.services import asset_server_control as m

    monkeypatch.setattr(m.settings, "host_runner_enabled", True)
    s = AssetServerControl(
        mkdb(
            host_access_rows=[
                Obj(
                    cluster_id=1,
                    node_name="pve-lab-01",
                    status="host_runner",
                    encrypted_private_key=None,
                    key_ref=None,
                )
            ]
        )
    )
    try:
        s.action("start", "iso")
        assert False
    except HostRunnerNotConfiguredError:
        assert True


def test_invalid_port_rejected(monkeypatch):
    from app.services import asset_server_control as m

    monkeypatch.setattr(m.settings, "host_runner_enabled", True)
    s = AssetServerControl(
        mkdb(
            host_access_rows=[
                Obj(
                    cluster_id=1,
                    node_name="pve-lab-01",
                    status="host_runner",
                    encrypted_private_key="x",
                )
            ]
        )
    )
    try:
        s.action("install", "iso", port=9999)
        assert False
    except ValueError as e:
        assert "port must be 8088" in str(e)
