import base64
import hashlib
from app.core.config import settings

try:
    from cryptography.fernet import Fernet
except Exception:  # pragma: no cover
    Fernet = None


def _get_key_material() -> str:
    key = getattr(settings, "config_encryption_key", None) or getattr(
        settings, "app_secret_key", None
    )
    if not key:
        raise RuntimeError(
            "Missing CONFIG_ENCRYPTION_KEY or APP_SECRET_KEY for secret encryption"
        )
    return key


def _build_fernet() -> "Fernet":
    if Fernet is None:
        raise RuntimeError("cryptography package is required for secret encryption")
    digest = hashlib.sha256(_get_key_material().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
