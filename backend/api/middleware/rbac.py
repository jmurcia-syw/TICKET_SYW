from functools import wraps
from flask import g, jsonify
from backend.api.middleware.auth import jwt_required_active


def require_role(*role_names: str):
    """Decorator: require JWT (active user) + one of the given role names."""
    def decorator(fn):
        @wraps(fn)
        @jwt_required_active
        def wrapper(*args, **kwargs):
            user = g.current_user
            if user.role.name not in role_names:
                return jsonify({"error": "forbidden", "message": "Acceso denegado"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
