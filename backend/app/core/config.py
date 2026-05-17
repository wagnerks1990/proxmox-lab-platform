from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60

    proxmox_base_url: str
    proxmox_token_id: str
    proxmox_token_secret: str
    proxmox_verify_ssl: bool = False

    lab_vm_ssh_username: str | None = None
    lab_vm_ssh_password: str | None = None

    heartbeat_timeout_seconds: int = 60
    session_reconnect_timeout_seconds: int = 180
    session_idle_timeout_seconds: int = 900

    reconnect_token_ttl_seconds: int = 300
    reconnect_token_secret: str | None = None

    worker_scheduler_enabled: bool = True
    session_cleanup_interval_seconds: int = 60
    health_poll_interval_seconds: int = 60
    reconciliation_interval_seconds: int = 300

    replay_store_backend: str = 'memory'
    worker_lock_backend: str = 'memory'


settings = Settings()
