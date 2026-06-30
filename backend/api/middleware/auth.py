from functools import wraps
from flask import g, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from backend.infra.repositories.user_repo import UserRepository
from backend.infra.database import get_db
import uuid


def jwt_required_active(fn):
    """Verify JWT and check that the user account is still active."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id_str = get_jwt_identity()
        db = next(get_db())
        repo = UserRepository(db)
        user = repo.get_by_id(uuid.UUID(user_id_str))
        if not user or not user.active:
            from flask import jsonify
            return jsonify({"error": "unauthorized", "message": "Acceso denegado"}), 401
        g.current_user = user
        return fn(*args, **kwargs)
    return wrapper
