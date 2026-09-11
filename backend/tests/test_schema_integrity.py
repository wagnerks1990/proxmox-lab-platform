import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.api.routers.admin_users import _normalize_template_ids
from app.db.session import Base


@pytest.fixture
def engine():
    value = create_engine("sqlite://")
    Base.metadata.create_all(value)
    try:
        yield value
    finally:
        Base.metadata.drop_all(value)


@pytest.mark.parametrize(
    "statement",
    [
        """
        INSERT INTO organization_memberships
            (organization_id, user_id, role, is_active)
        VALUES (1, 1, 'superuser', true)
        """,
        """
        INSERT INTO lab_runs
            (organization_id, lab_id, name, state, max_vms_per_student, created_by)
        VALUES (1, 1, 'Invalid quota', 'draft', 0, 1)
        """,
        """
        INSERT INTO lab_assignments
            (organization_id, lab_run_id, user_id, template_id, slot_index, status)
        VALUES (1, 1, 1, 1, 0, 'assigned')
        """,
    ],
)
def test_migration_check_constraints_are_present_in_model_metadata(engine, statement):
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(statement))


def test_permission_pair_is_unique_and_payload_ids_are_normalized(engine):
    assert _normalize_template_ids([9, "9", 10, 9]) == [9, 10]
    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO permissions (user_id, template_id) VALUES (1, 9)")
        )
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO permissions (user_id, template_id) VALUES (1, 9)")
            )


def test_vmid_is_unique_within_cluster_but_reusable_across_clusters(engine):
    insert = text(
        """
        INSERT INTO student_vms
            (organization_id, proxmox_cluster_id, owner_id, template_id,
             vm_name, vmid, proxmox_node)
        VALUES
            (:organization_id, :cluster_id, :owner_id, :template_id,
             :vm_name, :vmid, :node)
        """
    )
    base = {
        "organization_id": 1,
        "owner_id": 1,
        "template_id": 1,
        "vmid": 200000,
        "node": "pve-1",
    }
    with engine.begin() as connection:
        connection.execute(insert, {**base, "cluster_id": 1, "vm_name": "cluster-1"})
        connection.execute(insert, {**base, "cluster_id": 2, "vm_name": "cluster-2"})
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                insert, {**base, "cluster_id": 1, "vm_name": "cluster-1-duplicate"}
            )
