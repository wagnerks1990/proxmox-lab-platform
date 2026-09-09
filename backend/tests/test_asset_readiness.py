import pytest
from app.api.routers import proxmox_assets


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

    def all(self):
        return self.rows


class DB:
    def __init__(self, required=False):
        from app.models.models import ProxmoxCluster, AssetCatalog

        self.map = {
            ProxmoxCluster: [Obj(id=1, is_active=True)],
            AssetCatalog: [Obj(id=1, is_required=True)] if required else [],
        }

    def query(self, model):
        return Q(self.map.get(model, []))


@pytest.mark.asyncio
async def test_readiness_empty_catalog_warn(monkeypatch):
    async def inv(**kwargs):
        return {
            "nodes": [{"node": "pve-lab-01", "status": "online"}],
            "iso_by_node": [],
            "ct_templates_by_node": [],
            "vm_templates_by_node": [],
            "errors_by_node": {},
            "generated_at": "x",
        }

    monkeypatch.setattr(proxmox_assets, "assets_inventory", inv)
    out = await proxmox_assets.assets_readiness(_user=Obj(), db=DB(required=False))
    assert out["status"] == "WARN"
    assert "vm_template_vmid_by_node" in out
    assert "generated_at" in out


@pytest.mark.asyncio
async def test_readiness_missing_vm_detected(monkeypatch):
    async def inv(**kwargs):
        return {
            "nodes": [
                {"node": "pve-lab-01", "status": "online"},
                {"node": "pve-lab-02", "status": "online"},
            ],
            "iso_by_node": [
                {"node": "pve-lab-01", "items": [{"filename": "a.iso"}]},
                {"node": "pve-lab-02", "items": [{"filename": "a.iso"}]},
            ],
            "ct_templates_by_node": [
                {"node": "pve-lab-01", "items": []},
                {"node": "pve-lab-02", "items": []},
            ],
            "vm_templates_by_node": [
                {
                    "node": "pve-lab-01",
                    "templates": [
                        {
                            "name": "Ubuntu2604LTSv1c451c4",
                            "vmid": 303,
                            "template": 1,
                            "status": "stopped",
                        }
                    ],
                },
                {"node": "pve-lab-02", "templates": []},
            ],
            "errors_by_node": {},
            "generated_at": "x",
        }

    monkeypatch.setattr(proxmox_assets, "assets_inventory", inv)
    out = await proxmox_assets.assets_readiness(_user=Obj(), db=DB(required=True))
    assert out["status"] == "WARN"
    assert "pve-lab-02" in out["missing_vm_templates_by_node"]
    required_keys = {
        "ok",
        "status",
        "asset_ready_nodes",
        "constrained_nodes",
        "missing_isos_by_node",
        "missing_ct_templates_by_node",
        "missing_vm_templates_by_node",
        "vm_template_vmid_by_node",
        "recommended_next_steps",
        "errors_by_node",
        "generated_at",
    }
    assert required_keys.issubset(set(out.keys()))
