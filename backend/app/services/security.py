"""Password hashing and signed tokens using only the Python standard library."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1
TOKEN_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(dk).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(dk_b64)
        dk = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def _secret() -> bytes:
    env = os.environ.get("DRIFTAI_SECRET")
    if env:
        return env.encode()
    path = Path(os.environ.get("DRIFTAI_SECRET_FILE", ".driftai_secret"))
    if path.exists():
        return path.read_text().strip().encode()
    value = secrets.token_hex(32)
    path.write_text(value)
    return value.encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(user_id: int, ttl: int = TOKEN_TTL_SECONDS, now: float | None = None) -> str:
    payload = {"uid": user_id, "exp": int((now if now is not None else time.time()) + ttl)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
    return body + "." + sig


def read_token(token: str, now: float | None = None) -> int | None:
    """Return the user id if the token is valid and not expired, else None."""
    try:
        body, sig = token.split(".")
        good = _b64(hmac.new(_secret(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, good):
            return None
        payload = json.loads(_unb64(body))
        if payload["exp"] < (now if now is not None else time.time()):
            return None
        return int(payload["uid"])
    except Exception:
        return None