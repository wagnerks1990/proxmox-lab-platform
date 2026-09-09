from app.core.request_context import get_request_id


def api_success(data=None, message: str = "") -> dict:
    return {
        "success": True,
        "data": data if data is not None else {},
        "message": message,
        "error": None,
        "request_id": get_request_id(),
    }


def api_error(message: str, error=None) -> dict:
    return {
        "success": False,
        "data": {},
        "message": message,
        "error": error if error is not None else {"message": message},
        "request_id": get_request_id(),
    }
