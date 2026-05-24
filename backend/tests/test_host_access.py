from app.services.secret_crypto import decrypt_secret
from app.models.models import ProxmoxHostAccess


def test_host_access_model_encrypt_roundtrip(db_session):
    secret = 'runner-private-key'
    row = ProxmoxHostAccess(cluster_id=1, node_name='pve-lab-01', encrypted_private_key='')
    from app.services.secret_crypto import encrypt_secret
    row.encrypted_private_key = encrypt_secret(secret)
    assert decrypt_secret(row.encrypted_private_key) == secret


def test_status_shape_never_contains_private_key(client, admin_headers):
    r = client.get('/api/admin/proxmox/host-access/status?cluster_id=1', headers=admin_headers)
    if r.status_code == 200:
      assert 'encrypted_private_key' not in r.text
