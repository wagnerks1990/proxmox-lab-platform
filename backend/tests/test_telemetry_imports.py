from app.schemas.telemetry import TelemetrySummary
from app.api.routers import admin_telemetry


def test_imports():
    assert TelemetrySummary(total_events=0, failures=0, session_events=0)
    assert admin_telemetry.router is not None
