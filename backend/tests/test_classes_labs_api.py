import pytest

from app.main import app
from app.api.routers import classes_labs
from app.models.models import Class, Enrollment, Lab, OrganizationMembership, User
from app.schemas.classes_labs import ClassCreate, EnrollmentCreate, LabCreate
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


class FakeDB:
    def __init__(self, mapping):
        self.mapping = mapping

    def query(self, model):
        return FakeQuery(self.mapping.get(model, []))

    def add(self, obj):
        if not getattr(obj, "id", None):
            obj.id = 1

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def test_class_and_lab_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/admin/classes" in paths
    assert "/api/admin/labs" in paths


def test_student_cannot_manage_classes_and_labs(monkeypatch):
    organization = OrganizationContext(id=4, slug="science", role="student")
    db = FakeDB({Class: [], Lab: []})
    with pytest.raises(Exception) as exc:
        classes_labs.create_class(
            ClassCreate(name="X"), _user=Obj(id=1), organization=organization, db=db
        )
    assert getattr(exc.value, "status_code", None) == 403

    with pytest.raises(Exception) as exc2:
        import asyncio

        asyncio.run(
            classes_labs.create_lab(
                LabCreate(class_id=1, name="L1", default_pool_id=1),
                _user=Obj(id=1),
                organization=organization,
                db=db,
            )
        )
    assert getattr(exc2.value, "status_code", None) == 403


def test_admin_create_class_and_enrollment_duplicate(monkeypatch):
    organization = OrganizationContext(id=4, slug="science", role="owner")
    db = FakeDB({User: [Obj(id=2)], Class: [], Enrollment: []})
    out = classes_labs.create_class(
        ClassCreate(name="BIO101", term="2026S"),
        _user=Obj(id=1),
        organization=organization,
        db=db,
    )
    assert out.success is True
    assert out.data.organization_id == 4

    db2 = FakeDB(
        {
            Class: [Obj(id=1, organization_id=4)],
            OrganizationMembership: [
                Obj(user_id=2, organization_id=4, role="student", is_active=True)
            ],
            Enrollment: [Obj(id=9, class_id=1, user_id=2, role="student")],
        }
    )
    e = classes_labs.add_enrollment(
        1,
        EnrollmentCreate(user_id=2, role="student"),
        _user=Obj(id=1),
        organization=organization,
        db=db2,
    )
    assert e.success is True
    assert e.data.id == 9
