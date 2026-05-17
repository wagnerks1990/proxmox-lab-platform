from app.services.runtime_supervisor_service import RuntimeSupervisorService
from app.services.validation_service import ValidationService
from app.api.routers import admin_runtime, admin_validation


def test_imports():
    assert RuntimeSupervisorService
    assert ValidationService
    assert admin_runtime.router and admin_validation.router
