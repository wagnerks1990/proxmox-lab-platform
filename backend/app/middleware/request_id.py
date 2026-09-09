import uuid
import re
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        supplied = request.headers.get("X-Request-ID", "")
        request_id = (
            supplied
            if len(supplied) <= 128 and re.fullmatch(r"[A-Za-z0-9._:-]+", supplied)
            else str(uuid.uuid4())
        )
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
