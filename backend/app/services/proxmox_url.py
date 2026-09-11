from urllib.parse import urlsplit, urlunsplit

from app.core.config import settings


def canonicalize_proxmox_api_url(value: str, *, verify_ssl: bool) -> str:
    """Return a canonical Proxmox API URL or fail closed.

    The API credential is scoped operationally to this origin, so accepting a
    loose URL here would turn later authenticated probes into credential
    exfiltration requests.
    """
    raw = str(value or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme.lower() != "https":
        raise ValueError("Proxmox API URL must use HTTPS")
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Proxmox API URL must contain a host and no credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("Proxmox API URL must not contain a query or fragment")
    if parsed.path.rstrip("/") != "/api2/json":
        raise ValueError("Proxmox API URL path must be /api2/json")
    if not verify_ssl and not settings.proxmox_allow_insecure_tls:
        raise ValueError(
            "Disabling Proxmox TLS verification is prohibited by host policy"
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Proxmox API URL has an invalid port") from exc
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    netloc = host if port in (None, 443) else f"{host}:{port}"
    return urlunsplit(("https", netloc, "/api2/json", "", ""))
