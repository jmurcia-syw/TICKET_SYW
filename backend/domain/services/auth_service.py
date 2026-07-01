from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash


class AuthService:
    def hash_password(self, password: str) -> str:
        return generate_password_hash(password)

    def verify_password(self, password: str, password_hash: Optional[str]) -> bool:
        if not password_hash:
            return False
        return check_password_hash(password_hash, password)
