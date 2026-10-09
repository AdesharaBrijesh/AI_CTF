"""larkspur-api — service entrypoint."""
from flask import Flask, jsonify

from config import settings
from routes.shipments import shipments_bp
from routes.webhooks import webhooks_bp


def create_app():
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    app.config["ENV_NAME"] = settings.ENV_NAME

    app.register_blueprint(shipments_bp, url_prefix="/api/v1/shipments")
    app.register_blueprint(webhooks_bp, url_prefix="/api/v1/webhooks")

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok", "env": settings.ENV_NAME,
                        "version": settings.VERSION})

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=settings.PORT, debug=settings.DEBUG)
