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

    guacamole_internal_url: str = 'http://127.0.0.1:8080/guacamole'
    guacamole_base_url: str = '/guacamole'
    guacamole_admin_user: str | None = None
    guacamole_admin_password: str | None = None
    guacamole_datasource: str | None = 'postgresql'
    guacamole_enabled: bool = True
    guacamole_default_protocol: str = 'rdp'
    guacamole_verify_ssl: bool = False


settings = Settings()
