PROTOCOL_REGISTRY = {
    "novnc": {"implemented": False, "message": "not implemented yet"},
    "guacamole": {"implemented": False, "message": "not implemented yet"},
    "rdp": {"implemented": True, "message": "rdp download flow available"},
    "spice": {"implemented": False, "message": "spice is disabled"},
    "web_terminal": {"implemented": True, "message": "web terminal scaffold available"},
}


def get_protocol_info(name: str) -> dict:
    return PROTOCOL_REGISTRY.get(
        name, {"implemented": False, "message": "not implemented yet"}
    )
