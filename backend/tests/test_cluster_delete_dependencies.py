from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routers.admin_proxmox_setup import delete_cluster
from app.db.session import Base
from app.models.models import (
    Organization,
    ProxmoxCluster,
    Role,
    StudentVM,
    User,
    VMTemplate,
)


def test_cluster_delete_returns_dependency_counts_instead_of_fk_failure():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    try:
        organization = Organization(name="Test", slug="test", enabled=True)
        cluster = ProxmoxCluster(
            name="pve-test", api_url="https://pve.invalid", is_active=True
        )
        role = Role(name="Student")
        db.add_all([organization, cluster, role])
        db.flush()
        owner = User(
            username="student",
            email="student@example.test",
            password_hash="not-used",
            role_id=role.id,
        )
        db.add(owner)
        db.flush()
        template = VMTemplate(
            organization_id=organization.id,
            proxmox_cluster_id=cluster.id,
            name="Template",
            proxmox_node="pve-1",
            source_vmid=9000,
        )
        db.add(template)
        db.flush()
        db.add(
            StudentVM(
                organization_id=organization.id,
                proxmox_cluster_id=cluster.id,
                owner_id=owner.id,
                template_id=template.id,
                vm_name="historical-vm",
                vmid=200000,
                proxmox_node="pve-1",
            )
        )
        db.commit()

        with pytest.raises(HTTPException) as raised:
            delete_cluster(cluster.id, _user=SimpleNamespace(id=1), db=db)

        assert raised.value.status_code == 409
        assert raised.value.detail["dependencies"] == {
            "templates": 1,
            "vm_history": 1,
        }
        assert db.query(ProxmoxCluster).filter_by(id=cluster.id).one()
    finally:
        db.close()
        Base.metadata.drop_all(engine)
