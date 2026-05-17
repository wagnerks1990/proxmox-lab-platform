def test_scheduler_importable():
    from app.workers.scheduler import start_scheduler, stop_scheduler
    assert start_scheduler and stop_scheduler
