import os
from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.database import get_db
from backend.domain.entities.user import User
import uuid

# DEV MODE: set DEV_SKIP_AUTH=true in .env to bypass JWT on all endpoints
_DEV_SKIP = os.environ.get("DEV_SKIP_AUTH", "false").lower() == "true"


def _set_dev_user():
    """Injects a fake admin user into g so endpoint code works normally."""
    import uuid as _uuid
    from datetime import datetime
    from backend.domain.entities.role import Role

    if not hasattr(g, "current_user"):
        g.current_user = User(
            id=_uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="dev@sywork.net",
            username="dev",
            role=Role(id=_uuid.UUID("00000000-0000-0000-0000-000000000002"), name="Admin"),
            active=True,
            created_at=datetime.utcnow(),
        )


def jwt_required_active(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if _DEV_SKIP:
            _set_dev_user()
            return fn(*args, **kwargs)
        verify_jwt_in_request()
        user_id_str = get_jwt_identity()
        db = get_db()
        repo = UserRepository(db)
        user = repo.get_by_id(uuid.UUID(user_id_str))
        if not user or not user.active:
            return {"error": "unauthorized", "message": "Acceso denegado"}, 401
        g.current_user = user
        return fn(*args, **kwargs)
    return wrapper
