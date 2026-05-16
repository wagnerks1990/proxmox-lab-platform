import logging
from typing import Any

logger = logging.getLogger('proxmox_lab')


def log_event(event: str, **fields: Any) -> None:
    payload = {'event': event, **fields}
    logger.info(payload)
