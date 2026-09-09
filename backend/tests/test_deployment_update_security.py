from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services.deployment_updates import DeploymentUpdateService


class _Db:
    def __init__(self):
        self.row = SimpleNamespace(
            branch="main",
            channel="stable",
            automatic_updates=False,
            check_interval_minutes=360,
            maintenance_hour_utc=7,
            updated_at=None,
        )

    def query(self, _model):
        return self

    def order_by(self, *_args):
        return self

    def first(self):
        return self.row

    def add(self, _row):
        pass

    def commit(self):
        pass

    def refresh(self, _row):
        pass


@pytest.mark.parametrize("value", ["../main", "main..evil", "-danger", "bad ref", ""])
def test_update_settings_reject_unsafe_git_references(value):
    with pytest.raises(HTTPException) as exc:
        DeploymentUpdateService(_Db()).update_settings({"branch": value}, actor_id=1)
    assert exc.value.status_code == 422


def test_update_settings_accept_normal_release_reference():
    row = DeploymentUpdateService(_Db()).update_settings(
        {"branch": "release/v2.1.0"}, actor_id=1
    )
    assert row.branch == "release/v2.1.0"


def test_automatic_updates_fail_closed_without_host_policy(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "updater_allow_automatic", False)
    monkeypatch.setattr(settings, "updater_require_signed_commits", False)
    with pytest.raises(HTTPException) as exc:
        DeploymentUpdateService(_Db()).update_settings(
            {"automatic_updates": True}, actor_id=1
        )
    assert exc.value.status_code == 409
