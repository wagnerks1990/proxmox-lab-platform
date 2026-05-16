from app.core.config import settings


def guacamole_configured() -> bool:
    return bool(settings.guacamole_base_url and settings.guacamole_admin_user and settings.guacamole_admin_password)


def build_launch_url(vm_id: int, protocol: str = 'rdp') -> str:
    base = (settings.guacamole_base_url or '').rstrip('/')
    return f"{base}/#/client/{protocol}-{vm_id}"
