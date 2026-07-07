import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash

RESET_TOKEN_TTL = timedelta(minutes=30)


class AuthService:
    def hash_password(self, password: str) -> str:
        return generate_password_hash(password)

    def verify_password(self, password: str, password_hash: Optional[str]) -> bool:
        if not password_hash:
            return False
        return check_password_hash(password_hash, password)

    def generate_reset_token(self) -> tuple[str, datetime]:
        """Token de un solo uso + su expiración (ahora + 30 min)."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + RESET_TOKEN_TTL
        return token, expires_at

    def is_reset_token_valid(self, user, token: str) -> bool:
        """Válido si coincide, no expiró, y la cuenta está activa (FR-009, FR-010, FR-012)."""
        if not user or not user.active or not user.reset_token or not user.reset_token_expires_at:
            return False
        if user.reset_token != token:
            return False
        expires_at = user.reset_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at > datetime.now(timezone.utc)
