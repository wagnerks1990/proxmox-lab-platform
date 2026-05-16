from __future__ import annotations

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt


def create_reconnect_token(*, secret: str, session_id: int, user_id: int, protocol: str, ttl_seconds: int, fingerprint: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=ttl_seconds)
    payload = {
        'sid': session_id,
        'uid': user_id,
        'proto': protocol,
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
    }
    if fingerprint:
        payload['fp'] = fingerprint
    return jwt.encode(payload, secret, algorithm='HS256')


def verify_reconnect_token(*, token: str, secret: str, session_id: int, user_id: int, protocol: str, fingerprint: str | None = None) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
    except JWTError as exc:
        raise ValueError(f'invalid reconnect token: {exc}')
    if payload.get('sid') != session_id:
        raise ValueError('wrong session')
    if payload.get('uid') != user_id:
        raise ValueError('wrong user')
    if payload.get('proto') != protocol:
        raise ValueError('wrong protocol')
    if fingerprint and payload.get('fp') not in {None, fingerprint}:
        raise ValueError('wrong fingerprint')
    return payload
