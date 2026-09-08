import pytest

from app.main import app
from app.api.routers import pools
from app.models.models import DesktopPool, VMTemplate, ProxmoxCluster, ProxmoxNode, ProxmoxClusterDefault
from app.schemas.pools import PoolCreate
from app.services.organization_access import OrganizationContext


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self.rows

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def count(self):
        return len(self.rows)

    def join(self, *args, **kwargs):
        return self


class FakeDB:
    def __init__(self, mapping):
        self.mapping = mapping

    def query(self, model):
        return FakeQuery(self.mapping.get(model, []))

    def add(self, obj):
        pass

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def test_admin_pool_routes_registered():
    paths = set(app.openapi()['paths'])
    assert '/api/admin/pools' in paths
    assert '/api/admin/pools/{id}' in paths


@pytest.mark.asyncio
async def test_student_cannot_manage_pools(monkeypatch):
    db = FakeDB({DesktopPool: []})
    with pytest.raises(Exception) as exc:
        await pools.list_pools(_user=Obj(), organization=OrganizationContext(1, 'default', 'student'), db=db)
    assert getattr(exc.value, 'status_code', None) == 403


@pytest.mark.asyncio
async def test_create_rejects_missing_name(monkeypatch):
    db = FakeDB({ProxmoxCluster: [], DesktopPool: [], VMTemplate: []})
    payload = PoolCreate(name='', description=None, pool_type='persistent', template_vmid=None, template_node=None, default_protocol='NOVNC', target_node=None, storage=None, bridge=None, vlan_tag=None, vmid_start=None, vmid_end=None, naming_pattern=None, desired_size=0, maintenance_mode=False, enabled=True)
    with pytest.raises(Exception) as exc:
        await pools.create_pool(payload=payload, _user=Obj(id=1), organization=OrganizationContext(1, 'default', 'instructor'), db=db)
    assert getattr(exc.value, 'status_code', None) == 422


@pytest.mark.asyncio
async def test_create_rejects_invalid_template(monkeypatch):
    db = FakeDB({VMTemplate: [], ProxmoxCluster: [], DesktopPool: []})
    payload = PoolCreate(name='lab', description=None, pool_type='persistent', template_vmid=999, template_node=None, default_protocol='NOVNC', target_node=None, storage=None, bridge=None, vlan_tag=None, vmid_start=None, vmid_end=None, naming_pattern=None, desired_size=0, maintenance_mode=False, enabled=True)
    with pytest.raises(Exception) as exc:
        await pools.create_pool(payload=payload, _user=Obj(id=1), organization=OrganizationContext(1, 'default', 'owner'), db=db)
    assert getattr(exc.value, 'status_code', None) == 422


@pytest.mark.asyncio
async def test_list_includes_readiness_hints(monkeypatch):

    async def fake_templates(_):
        return [{'vmid': 303, 'node': 'pve-lab-01'}]

    async def fake_isos(_):
        return {'items': [{'node': 'pve-lab-01', 'content_id': 'local:iso/a.iso'}], 'warnings': []}

    monkeypatch.setattr(pools.ProxmoxBootstrapService, 'discover_templates', lambda self, active: fake_templates(active))
    monkeypatch.setattr(pools.ProxmoxBootstrapService, 'discover_isos', lambda self, active: fake_isos(active))

    db = FakeDB({
        DesktopPool: [Obj(id=1, organization_id=1, name='pool', pool_type='persistent', template_vmid=303, template_node='pve-lab-01', default_protocol='NOVNC', desired_size=1, maintenance_mode=False, enabled=True, created_at=None, updated_at=None)],
        ProxmoxCluster: [Obj(id=1, is_active=True)],
        ProxmoxNode: [Obj(node_name='pve-lab-01', status='online'), Obj(node_name='pve-lab-02', status='online')],
        ProxmoxClusterDefault: [Obj(placement_policy='balanced')],
        VMTemplate: [Obj(id=1, source_vmid=303, proxmox_node='pve-lab-01')],
    })
    out = await pools.list_pools(_user=Obj(id=1), organization=OrganizationContext(1, 'default', 'owner'), db=db)
    row = out.data[0]
    assert hasattr(row, 'readiness_status')
    assert hasattr(row, 'placement_warning')
    assert hasattr(row, 'asset_ready_nodes')
    assert hasattr(row, 'constrained_nodes')
    assert hasattr(row, 'missing_templates_by_node')
    assert hasattr(row, 'missing_isos_by_node')
    assert hasattr(row, 'recommended_next_steps')
