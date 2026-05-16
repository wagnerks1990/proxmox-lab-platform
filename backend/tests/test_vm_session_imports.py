def test_vm_session_model_importable():
    from app.models.models import VMSession
    assert VMSession is not None


def test_vm_session_migration_importable():
    import importlib
    mod = importlib.import_module('alembic.versions.20260516_0003_vm_sessions')
    assert mod.revision == '20260516_0003'
