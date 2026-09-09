import uuid
from fastapi import Request
from starlette.responses import Response

from app.core.request_context import set_request_id


async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    set_request_id(request_id)
    response: Response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response
