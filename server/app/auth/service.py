"""HMAC 签名 Cookie 签发/校验（24h 时效），nginx auth_request 依赖本模块语义"""

import base64
import hashlib
import hmac
import json
import time

from app.config import TOKEN_TTL, cfg


def issue_token(user: str) -> str:
    payload = {'usr': user, 'exp': int(time.time()) + TOKEN_TTL}
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).decode()
    sig = hmac.new(cfg.APP_SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f'{raw}.{sig}'


def verify_token(token: str | None) -> dict | None:
    if not token or '.' not in token:
        return None
    raw, sig = token.rsplit('.', 1)
    expect = hmac.new(cfg.APP_SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expect):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(raw.encode()))
    except Exception:
        return None
    if int(payload.get('exp', 0)) < int(time.time()):
        return None
    return payload
