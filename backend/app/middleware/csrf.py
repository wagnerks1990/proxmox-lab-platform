from urllib.parse import urlsplit

from fastapi import WebSocket
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings


def _canonical_origin(value: str) -> str | None:
    parsed = urlsplit((value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    if parsed.username or parsed.password or parsed.path not in {"", "/"}:
        return None
    if parsed.query or parsed.fragment:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    default = 443 if parsed.scheme == "https" else 80
    return f"{parsed.scheme}://{host}" + (
        f":{port}" if port and port != default else ""
    )


def _trusted_origins(
    *, host: str, forwarded_proto: str | None, scheme: str
) -> set[str]:
    configured = {
        canonical
        for value in settings.browser_trusted_origins.split(",")
        if (canonical := _canonical_origin(value))
    }
    if configured:
        return configured
    proto = (forwarded_proto or scheme).split(",", 1)[0].strip().lower()
    if proto in {"ws", "wss"}:
        proto = "https" if proto == "wss" else "http"
    derived = _canonical_origin(f"{proto}://{host}")
    return {derived} if derived else set()


def websocket_origin_allowed(websocket: WebSocket) -> bool:
    origin = _canonical_origin(websocket.headers.get("origin", ""))
    trusted = _trusted_origins(
        host=websocket.headers.get("host", ""),
        forwarded_proto=websocket.headers.get("x-forwarded-proto"),
        scheme=websocket.url.scheme,
    )
    return origin is not None and origin in trusted


class CookieCsrfMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        uses_cookie = bool(
            request.cookies.get(settings.auth_cookie_name)
        ) and not authorization.lower().startswith("bearer ")
        if not uses_cookie:
            return await call_next(request)

        fetch_site = request.headers.get("sec-fetch-site", "").lower()
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            return JSONResponse(
                status_code=403, content={"detail": "Cross-origin request denied"}
            )
        origin_header = request.headers.get("origin")
        if origin_header:
            origin = _canonical_origin(origin_header)
            trusted = _trusted_origins(
                host=request.headers.get("host", ""),
                forwarded_proto=request.headers.get("x-forwarded-proto"),
                scheme=request.url.scheme,
            )
            if origin is None or origin not in trusted:
                return JSONResponse(
                    status_code=403, content={"detail": "Cross-origin request denied"}
                )
        elif fetch_site != "same-origin":
            return JSONResponse(
                status_code=403, content={"detail": "CSRF verification required"}
            )
        return await call_next(request)
