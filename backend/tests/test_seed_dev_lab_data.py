from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.models import DesktopPool, Organization, VMTemplate
from scripts import seed_dev_lab_data


def _database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


def test_seed_data_is_idempotent_and_scoped_by_organization(monkeypatch):
    engine, db = _database()
    try:
        first = Organization(name="First", slug="first", enabled=True)
        second = Organization(name="Second", slug="second", enabled=True)
        db.add_all([first, second])
        db.commit()
        monkeypatch.setenv("DEV_TEMPLATE_NAME", "Shared template")
        monkeypatch.setenv("DEV_TEMPLATE_VMID", "9000")
        monkeypatch.setenv("DEV_TEMPLATE_NODE", "pve-a")
        monkeypatch.setenv("DEV_DESKTOP_POOL_NAME", "Shared pool")

        seed_dev_lab_data.seed_template(db, first)
        seed_dev_lab_data.seed_desktop_pool(db, first)
        db.commit()

        monkeypatch.setenv("DEV_TEMPLATE_VMID", "9001")
        monkeypatch.setenv("DEV_TEMPLATE_NODE", "pve-b")
        seed_dev_lab_data.seed_template(db, second)
        seed_dev_lab_data.seed_desktop_pool(db, second)
        seed_dev_lab_data.seed_template(db, second)
        seed_dev_lab_data.seed_desktop_pool(db, second)
        db.commit()

        templates = db.query(VMTemplate).order_by(VMTemplate.organization_id).all()
        pools = db.query(DesktopPool).order_by(DesktopPool.organization_id).all()
        assert [(row.organization_id, row.source_vmid) for row in templates] == [
            (first.id, 9000),
            (second.id, 9001),
        ]
        assert [(row.organization_id, row.template_vmid) for row in pools] == [
            (first.id, 9000),
            (second.id, 9001),
        ]
    finally:
        db.close()
        Base.metadata.drop_all(engine)


def test_seed_main_requires_organization_slug(monkeypatch, capsys):
    monkeypatch.delenv("DEV_ORGANIZATION_SLUG", raising=False)
    assert seed_dev_lab_data.main() == 1
    assert "DEV_ORGANIZATION_SLUG is required" in capsys.readouterr().out
