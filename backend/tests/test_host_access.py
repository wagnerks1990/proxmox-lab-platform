from app.services.secret_crypto import decrypt_secret, encrypt_secret
from app.models.models import ProxmoxHostAccess


def test_host_access_model_encrypt_roundtrip():
    secret = "runner-private-key"
    row = ProxmoxHostAccess(
        cluster_id=1, node_name="pve-lab-01", encrypted_private_key=""
    )
    row.encrypted_private_key = encrypt_secret(secret)
    assert decrypt_secret(row.encrypted_private_key) == secret


def test_host_access_model_has_no_plaintext_secret_fields():
    row = ProxmoxHostAccess(cluster_id=1, node_name="pve-lab-01")
    assert not hasattr(row, "root_password")
    assert not hasattr(row, "private_key")
    assert hasattr(row, "encrypted_private_key")
