import os
from flask import Flask
from flask_restx import Api, Resource
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

load_dotenv()


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
        description="API para el sistema de tickets de soporte SYWork",
        doc="/swagger",
    )

    from backend.api.routes.auth import auth_bp
    from backend.api.routes.clients import clients_bp
    from backend.api.routes.projects import projects_bp
    from backend.api.routes.resources import resources_bp
    from backend.api.routes.users import users_bp

    for bp in (auth_bp, clients_bp, projects_bp, resources_bp, users_bp):
        app.register_blueprint(bp)

    ns_health = api.namespace("health", description="Health check")

    @ns_health.route("/")
    class Health(Resource):
        def get(self):
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
            except Exception as exc:
                return {
                    "status": "degraded",
                    "service": "sywork-backend",
                    "database": {"connected": False, "error": str(exc)},
                }, 503

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
