from datetime import datetime
from pydantic import BaseModel


class SessionActivityResponse(BaseModel):
    id: int
    actor_id: int
    vm_id: int
    protocol: str
    status: str
    details: str | None = None
    created_at: datetime | None = None
