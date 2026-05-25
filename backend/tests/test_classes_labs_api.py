import pytest

from app.api.routes import router
from app.api.routers import classes_labs
from app.models.models import Class, Enrollment, Lab, User, DesktopPool
from app.schemas.classes_labs import ClassCreate, EnrollmentCreate, LabCreate


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
        if not getattr(obj, 'id', None):
            obj.id = 1

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def _role(monkeypatch, role):
    monkeypatch.setattr(classes_labs, 'get_role_name', lambda _u: role)


def test_class_and_lab_routes_registered():
    paths = {r.path for r in router.routes}
    assert '/api/admin/classes' in paths
    assert '/api/admin/labs' in paths


def test_student_cannot_manage_classes_and_labs(monkeypatch):
    _role(monkeypatch, 'Student')
    db = FakeDB({Class: [], Lab: []})
    with pytest.raises(Exception) as exc:
        classes_labs.create_class(ClassCreate(name='X'), _user=Obj(id=1), db=db)
    assert getattr(exc.value, 'status_code', None) == 403

    with pytest.raises(Exception) as exc2:
        import asyncio
        asyncio.run(classes_labs.create_lab(LabCreate(class_id=1, name='L1', default_pool_id=1), _user=Obj(id=1), db=db))
    assert getattr(exc2.value, 'status_code', None) == 403


def test_admin_create_class_and_enrollment_duplicate(monkeypatch):
    _role(monkeypatch, 'Admin')
    db = FakeDB({User: [Obj(id=2)], Class: [], Enrollment: []})
    out = classes_labs.create_class(ClassCreate(name='BIO101', term='2026S'), _user=Obj(id=1), db=db)
    assert out.success is True

    db2 = FakeDB({Class: [Obj(id=1)], User: [Obj(id=2)], Enrollment: [Obj(id=9, class_id=1, user_id=2, role='student')]})
    e = classes_labs.add_enrollment(1, EnrollmentCreate(user_id=2, role='student'), _user=Obj(id=1), db=db2)
    assert e.success is True
    assert e.data.id == 9
