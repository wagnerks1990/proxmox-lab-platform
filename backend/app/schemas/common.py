from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


class ApiEnvelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    message: str = ""
    error: str | None = None
    request_id: str | None = None
