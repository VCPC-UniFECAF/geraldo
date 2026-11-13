import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings
from app.models import User


def hash_password(password: str, *, salt: bytes | None = None, iterations: int | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    iterations = iterations or settings.password_iterations
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Aceita somente HS256 e exige exp, sub, role e jti (docs/contracts/jwt.md)."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        options={"require": ["exp", "sub", "role", "jti"]},
    )
