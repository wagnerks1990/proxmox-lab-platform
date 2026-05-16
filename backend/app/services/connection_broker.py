from fastapi import HTTPException
from app.services.guacamole import guacamole_configured, build_launch_url


def get_guacamole_launch(vm_id: int, preferred_protocol: str = 'rdp', reachable: bool = True) -> dict:
    if not guacamole_configured():
        raise HTTPException(status_code=503, detail={'error': 'Guacamole not configured', 'guidance': 'Set GUACAMOLE_INTERNAL_URL and GUACAMOLE_BASE_URL'})
    if not reachable:
        raise HTTPException(status_code=503, detail={'error': 'Guacamole unreachable', 'guidance': 'Ensure local Guacamole is running at GUACAMOLE_INTERNAL_URL and proxied at /guacamole'})
    return {
        'type': 'guacamole',
        'protocol': preferred_protocol,
        'url': build_launch_url(vm_id, preferred_protocol),
        'message': 'Guacamole launch URL placeholder',
    }
