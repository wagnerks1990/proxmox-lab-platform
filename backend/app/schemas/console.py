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
    launch_url: str | None = None
    session_id: int | None = None
    protocol: str | None = None
    state: str | None = None
    reconnect_token: str | None = None
    heartbeat_interval_seconds: int | None = None
    expires_at: int | None = None
