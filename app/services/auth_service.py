import hashlib
import logging
import secrets
from datetime import datetime, timedelta
import jwt

# We import settings, and provide robust fallbacks
try:
    from app.core.config import settings
    SECRET_KEY = getattr(settings, "secret_key", "mg_secret_key_super_secure_39d8fjke9w8ujsdnc")
except Exception:
    SECRET_KEY = "mg_secret_key_super_secure_39d8fjke9w8ujsdnc"

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

logger = logging.getLogger("math_gap.auth_service")


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes plain password using secure native PBKDF2-SHA256 (OWASP standard)."""
        salt = secrets.token_hex(16)
        iterations = 100000
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
        return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies plain password against self-describing stored PBKDF2 hash."""
        try:
            parts = hashed_password.split("$")
            if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
                return False
            iterations = int(parts[1])
            salt = parts[2]
            original_hash = parts[3]
            dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations)
            return secrets.compare_digest(dk.hex(), original_hash)
        except Exception as exc:
            logger.error("Password verification error: %s", exc)
            return False

    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
        """Generates standard secure signed JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> dict | None:
        """Decodes and validates signed JWT token. Returns payload or None if signature/exp invalid."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except Exception:
            return None
