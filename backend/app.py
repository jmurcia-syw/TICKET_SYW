import logging
import os
from flask import Flask
from flask_restx import Api, Resource
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET", "change-me-in-production")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600 * 8

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)

    # Devuelve la conexión de PostgreSQL al pool al final de CADA request
    # (la sesión es request-scoped; sin esto el pool se agota bajo carga).
    from backend.infra.database import close_db
    app.teardown_appcontext(close_db)

    api = Api(
        app,
        version="1.0",
        title="SyWork Desk API",
        description=(
            "API para el sistema de tickets de soporte SYWork.\n\n"
            "**Seguridad (Fase 1)**: TODAS las rutas exigen JWT Bearer + permiso módulo/acción "
            "del rol del usuario. Rutas públicas: `/api/auth/login`, `/api/auth/google` y `/health/`."
        ),
        authorizations={
            "Bearer": {"type": "apiKey", "in": "header", "name": "Authorization",
                       "description": "Formato: Bearer {token}"},
        },
        security="Bearer",
        doc="/swagger",
    )

    # ── Auth (login provisional + Google OAuth2 + /me) ─────────────────────────
    from backend.api.routes.auth import ns as ns_auth
    api.add_namespace(ns_auth)

    # ── Maestros — namespaces con Swagger completo ────────────────────────────
    from backend.api.routes.clients import ns as ns_clients
    from backend.api.routes.projects import ns as ns_projects
    from backend.api.routes.resources import ns as ns_resources
    from backend.api.routes.users import ns as ns_users
    from backend.api.routes.roles import ns as ns_roles
    from backend.api.routes.permissions import ns as ns_permissions

    api.add_namespace(ns_clients)
    api.add_namespace(ns_projects)
    api.add_namespace(ns_resources)
    api.add_namespace(ns_users)
    api.add_namespace(ns_roles)
    api.add_namespace(ns_permissions)

    # ── Fase 1 — Tickets ──────────────────────────────────────────────────────
    from backend.api.routes.tickets import ns as ns_tickets
    from backend.api.routes.catalogs import ns as ns_catalogs
    from backend.api.routes.notifications import ns as ns_notifications
    from backend.api.routes.assignment_panel import ns as ns_panel

    api.add_namespace(ns_tickets)
    api.add_namespace(ns_catalogs)
    api.add_namespace(ns_notifications)
    api.add_namespace(ns_panel)

    # ── Health ────────────────────────────────────────────────────────────────
    ns_health = api.namespace("health", description="Estado del servicio y conectividad de DB")

    @ns_health.route("/")
    class Health(Resource):
        @ns_health.doc("health_check")
        @ns_health.response(200, "Servicio operativo")
        @ns_health.response(503, "Servicio degradado (DB no disponible)")
        def get(self):
            """Verificar estado del backend y conexión a PostgreSQL"""
            from backend.infra.database import get_db
            from sqlalchemy import text
            try:
                db = get_db()
                result = db.execute(text("SELECT version(), current_database(), now()")).fetchone()
                return {
                    "status": "ok",
                    "service": "sywork-backend",
                    "database": {
                        "connected": True,
                        "name": result[1],
                        "server_time": str(result[2]),
                        "version": result[0].split(",")[0],
                    },
                }
            except Exception:
                logger.exception("Health check failed: database unreachable")
                return {
                    "status": "degraded",
                    "service": "sywork-backend",
                    "database": {"connected": False, "error": "No se pudo conectar a la base de datos"},
                }, 503

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
