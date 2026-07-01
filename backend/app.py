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

    api = Api(
        app,
        version="1.0",
        title="SYWork Tickets API",
        description=(
            "API para el sistema de tickets de soporte SYWork.\n\n"
            "**Nota de desarrollo**: autenticación desactivada (`DEV_SKIP_AUTH=true`). "
            "Todos los endpoints son accesibles sin token JWT durante el desarrollo de Fase 0."
        ),
        doc="/swagger",
    )

    # ── Auth blueprint (OAuth2 + JWT — mantiene blueprint puro) ──────────────
    from backend.api.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    # ── Maestros — namespaces con Swagger completo ────────────────────────────
    from backend.api.routes.clients import ns as ns_clients
    from backend.api.routes.projects import ns as ns_projects
    from backend.api.routes.resources import ns as ns_resources
    from backend.api.routes.users import ns as ns_users

    api.add_namespace(ns_clients)
    api.add_namespace(ns_projects)
    api.add_namespace(ns_resources)
    api.add_namespace(ns_users)

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
                db = next(get_db())
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
