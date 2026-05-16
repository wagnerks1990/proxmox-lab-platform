from pydantic import BaseModel


class ConsoleLaunchResponse(BaseModel):
    type: str
    url: str | None = None
    host: str | None = None
    rdp_file: str | None = None
    novnc_url: str | None = None
    port: int | None = None
    ticket: str | None = None
    vmid: int | None = None
    node: str | None = None
