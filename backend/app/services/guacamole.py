import httpx
from app.core.config import settings


def guacamole_configured() -> bool:
    return bool(settings.guacamole_internal_url and settings.guacamole_base_url)


async def check_guacamole_reachable(timeout: float = 2.5) -> tuple[bool, str | None]:
    url = settings.guacamole_internal_url.rstrip('/') + '/'
    try:
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.get(url)
        if r.status_code < 500:
            return True, None
        return False, f'HTTP {r.status_code}'
    except Exception as exc:
        return False, str(exc)


def build_launch_url(vm_id: int, protocol: str = 'rdp') -> str:
    base = (settings.guacamole_base_url or '/guacamole').rstrip('/')
    return f"{base}/#/client/{protocol}-{vm_id}"
