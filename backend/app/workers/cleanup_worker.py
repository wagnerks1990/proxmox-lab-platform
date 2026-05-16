from app.workers.session_worker import run_once as session_cleanup_once


def run_once() -> dict[str, int]:
    return session_cleanup_once()
