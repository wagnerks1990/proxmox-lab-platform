def test_vm_session_model_importable():
    from app.models.models import VMSession

    assert VMSession is not None


def test_vm_session_is_part_of_canonical_baseline():
    from pathlib import Path

    baseline = Path("backend/alembic/versions/20260521_0001_canonical_dev_baseline.py")
    assert "vm_sessions" in baseline.read_text()
