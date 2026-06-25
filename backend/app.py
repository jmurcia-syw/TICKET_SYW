from flask import Flask
from flask_restx import Api, Resource
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

api = Api(
    app,
    version="1.0",
    title="SYWork Tickets API",
    description="API para el sistema de tickets de soporte SYWork",
    doc="/swagger",
)

ns = api.namespace("health", description="Health check")


@ns.route("/")
class Health(Resource):
    def get(self):
        return {"status": "ok", "service": "sywork-backend"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
