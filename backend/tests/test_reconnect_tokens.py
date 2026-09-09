import time
import pytest
from app.security.reconnect_tokens import create_reconnect_token, verify_reconnect_token


def test_valid_token():
    token = create_reconnect_token(
        secret="s", session_id=1, user_id=2, protocol="SSH_WS", ttl_seconds=60
    )
    assert verify_reconnect_token(
        token=token, secret="s", session_id=1, user_id=2, protocol="SSH_WS"
    )


def test_expired_token_rejected():
    token = create_reconnect_token(
        secret="s", session_id=1, user_id=2, protocol="SSH_WS", ttl_seconds=1
    )
    time.sleep(2)
    with pytest.raises(ValueError):
        verify_reconnect_token(
            token=token, secret="s", session_id=1, user_id=2, protocol="SSH_WS"
        )


def test_tampered_token_rejected():
    token = (
        create_reconnect_token(
            secret="s", session_id=1, user_id=2, protocol="SSH_WS", ttl_seconds=60
        )
        + "x"
    )
    with pytest.raises(ValueError):
        verify_reconnect_token(
            token=token, secret="s", session_id=1, user_id=2, protocol="SSH_WS"
        )
