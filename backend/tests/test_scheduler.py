from datetime import datetime, timezone

from app.workers.update_worker import should_check_for_update


def test_scheduler_importable():
    from app.workers.scheduler import start_scheduler, stop_scheduler

    assert start_scheduler and stop_scheduler


def test_maintenance_hour_forces_check_even_when_normal_interval_not_due():
    now = datetime(2026, 9, 11, 7, 5, tzinfo=timezone.utc)
    last = datetime(2026, 9, 11, 6, 50, tzinfo=timezone.utc)

    assert should_check_for_update(now, last, 360, 7) is True


def test_maintenance_hour_does_not_repeat_check_in_same_window():
    now = datetime(2026, 9, 11, 7, 45, tzinfo=timezone.utc)
    last = datetime(2026, 9, 11, 7, 5, tzinfo=timezone.utc)

    assert should_check_for_update(now, last, 360, 7) is False


def test_normal_interval_still_controls_checks_outside_maintenance_window():
    now = datetime(2026, 9, 11, 10, 0, tzinfo=timezone.utc)

    assert (
        should_check_for_update(
            now, datetime(2026, 9, 11, 9, 45, tzinfo=timezone.utc), 60, 7
        )
        is False
    )
    assert (
        should_check_for_update(
            now, datetime(2026, 9, 11, 8, 59, tzinfo=timezone.utc), 60, 7
        )
        is True
    )
