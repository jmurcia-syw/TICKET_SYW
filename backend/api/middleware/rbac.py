"""Enforcement de permisos módulo+acción en la API (FR-022, spec 002).

`@require_permission("tickets", "create")` exige: JWT válido → usuario activo → permiso.
Los permisos del rol se cargan una vez por request (cache en `g`). Errores 401/403 con
payload genérico, sin detalle del recurso solicitado (FR-023 spec 001).
"""
from functools import wraps

from flask import g

from backend.api.middleware.auth import jwt_required_active
from backend.infra.database import get_db
from backend.infra.repositories.role_repo import RoleRepository

_FORBIDDEN = ({"error": "forbidden", "message": "Acceso denegado"}, 403)
_UNAUTHORIZED = ({"error": "unauthorized", "message": "Acceso denegado"}, 401)


def _load_permissions() -> set[tuple[str, str]]:
    """Permisos (module, action) del rol del usuario actual, cacheados por request."""
    if not hasattr(g, "_permission_cache"):
        db = get_db()
        permissions = RoleRepository(db).list_permissions_for_role(g.current_user.role.id)
        g._permission_cache = {(p.module, p.action) for p in permissions}
    return g._permission_cache


def current_user_has(module: str, action: str) -> bool:
    """Chequeo puntual de permiso para lógica condicional dentro de un endpoint."""
    return (module, action) in _load_permissions()


def require_permission(module: str, action: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            protected = jwt_required_active(lambda: None)
            try:
                denied = protected()
            except Exception:
                # Token ausente/expirado/corrupto: flask-restx convertiría la excepción
                # de flask-jwt-extended en 500 — se mapea explícitamente a 401.
                return _UNAUTHORIZED
            if denied is not None:
                # jwt_required_active devolvió una respuesta (401 usuario inactivo)
                return denied
            if (module, action) not in _load_permissions():
                return _FORBIDDEN
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_authenticated():
    """JWT + usuario activo, sin exigir un permiso puntual — para endpoints que resuelven el
    permiso condicionalmente adentro (ej. `tickets:view` vs `tickets:view_own`, Fase 2.1)."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            protected = jwt_required_active(lambda: None)
            try:
                denied = protected()
            except Exception:
                return _UNAUTHORIZED
            if denied is not None:
                return denied
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def _action_for_request() -> str:
    from flask import request
    path = request.path.rstrip("/")
    if path.endswith("/activate") or path.endswith("/deactivate"):
        return "deactivate"
    return {
        "GET": "view", "POST": "create", "PATCH": "edit", "PUT": "edit", "DELETE": "deactivate",
    }.get(request.method, "view")


def enforce_module(module: str, allow_own_resource_edit: bool = False):
    """Enforcement por módulo para rutas existentes de maestros (FR-022 spec 002).

    Mapea el método HTTP a la acción (GET→view, POST→create, PATCH/PUT→edit,
    DELETE→deactivate, sufijos /activate|/deactivate→deactivate). Se aplica como
    `method_decorators` de los Resource de flask-restx.

    `allow_own_resource_edit`: excepción FR-012 (spec 001) — un usuario sin permiso de
    edición puede editar el registro de `resources` vinculado a su propia cuenta.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            protected = jwt_required_active(lambda: None)
            try:
                denied = protected()
            except Exception:
                return _UNAUTHORIZED
            if denied is not None:
                return denied
            action = _action_for_request()
            if (module, action) in _load_permissions():
                return fn(*args, **kwargs)
            if allow_own_resource_edit and action == "edit":
                resource_id = kwargs.get("resource_id")
                if resource_id and _is_own_resource(resource_id):
                    return fn(*args, **kwargs)
            return _FORBIDDEN
        return wrapper
    return decorator


def _is_own_resource(resource_id: str) -> bool:
    import uuid as _uuid
    from backend.infra.repositories.resource_repo import ResourceRepository
    try:
        rid = _uuid.UUID(str(resource_id))
    except ValueError:
        return False
    resource = ResourceRepository(get_db()).get_by_id(rid)
    return bool(resource and resource.user_id == g.current_user.id)


# Compatibilidad: alias del decorador previo (ya no usado en rutas nuevas)
def require_role(*role_names: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            protected = jwt_required_active(lambda: None)
            try:
                denied = protected()
            except Exception:
                return _UNAUTHORIZED
            if denied is not None:
                return denied
            if g.current_user.role.name not in role_names:
                return _FORBIDDEN
            return fn(*args, **kwargs)
        return wrapper
    return decorator
