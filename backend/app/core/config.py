from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    password_min_length: int = 12
    login_max_failures: int = 5
    login_failure_window_seconds: int = 300
    login_lockout_seconds: int = 900
    bootstrap_admin_token: str | None = None
    auth_cookie_name: str = "labgoblin_session"
    auth_cookie_secure: bool = False
    cors_allowed_origins: str = ""

    proxmox_base_url: str
    proxmox_token_id: str
    proxmox_token_secret: str
    proxmox_verify_ssl: bool = True
    app_secret_key: str | None = None
    config_encryption_key: str | None = None

    lab_vm_ssh_username: str | None = None
    lab_vm_ssh_password: str | None = None
    lab_vm_ssh_known_hosts: str | None = None
    lab_vm_ssh_private_key_path: str | None = None

    guacamole_internal_url: str | None = None
    guacamole_base_url: str = "/guacamole"
    guacamole_admin_user: str | None = None
    guacamole_admin_password: str | None = None
    guacamole_datasource: str = "postgresql"
    guacamole_verify_ssl: bool = True

    heartbeat_timeout_seconds: int = 60
    session_reconnect_timeout_seconds: int = 180
    session_idle_timeout_seconds: int = 900

    reconnect_token_ttl_seconds: int = 300
    reconnect_token_secret: str | None = None

    worker_scheduler_enabled: bool = True
    session_cleanup_interval_seconds: int = 60
    health_poll_interval_seconds: int = 60
    reconciliation_interval_seconds: int = 300
    operation_poll_interval_seconds: int = 2
    operation_lease_seconds: int = 180
    operation_max_attempts: int = 3

    replay_store_backend: str = "memory"
    worker_lock_backend: str = "memory"
    redis_url: str = "redis://redis:6379/0"
    asset_source_node: str | None = None
    asset_source_iso_base_url: str | None = None
    asset_source_ct_base_url: str | None = None
    host_runner_enabled: bool = False
    host_runner_user: str = "labgoblin-runner"
    host_runner_private_key_path: str | None = None
    asset_sync_poll_interval_seconds: int = 3
    asset_sync_download_timeout_seconds: int = 7200
    asset_sync_lease_seconds: int = 180

    updater_socket_path: str = "/var/lib/labgoblin/updater/updater.sock"
    updater_token: str | None = None
    # Keep this pointed at the repository's real URL until the GitHub repository
    # itself is renamed. It is an upstream location, not a product identifier.
    updater_repository: str = "https://github.com/wagnerks1990/proxmox-lab-platform.git"
    updater_poll_interval_seconds: int = 900
    updater_allow_automatic: bool = False
    updater_require_signed_commits: bool = False


settings = Settings()
