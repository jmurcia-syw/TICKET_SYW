from functools import wraps
from flask import g, jsonify
from backend.api.middleware.auth import jwt_required_active
from backend.domain.entities.user import Role


def require_role(*roles: str):
    """Decorator: require JWT (active user) + one of the given roles."""
    def decorator(fn):
        @wraps(fn)
        @jwt_required_active
        def wrapper(*args, **kwargs):
            user = g.current_user
            if user.role.value not in roles:
                return jsonify({"error": "forbidden", "message": "Acceso denegado"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
