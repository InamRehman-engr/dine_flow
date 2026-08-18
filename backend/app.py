import os

from flask import Flask
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import db, migrate, socketio
import models  # noqa: F401 — register models with SQLAlchemy
from routes.auth import auth_bp
from routes.menu import menu_bp
from routes.order import order_bp
from routes.tenant import tenant_bp
from routes.media import media_bp
from routes.stations import stations_bp
import routes.websocket  # noqa: F401 — register socket handlers


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "0") in (
        "1",
        "true",
        "True",
    )

    CORS(
        app,
        supports_credentials=True,
        origins="*",
    )

    db.init_app(app)
    migrate.init_app(app, db, directory="migrations")

    redis_url = app.config.get("REDIS_URL")
    socket_kwargs = {
        "cors_allowed_origins": "*",
        "manage_session": False,
    }
    if redis_url:
        socket_kwargs["message_queue"] = redis_url
    socketio.init_app(app, **socket_kwargs)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tenant_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(stations_bp)

    @app.get("/api/health")
    def health():
        from public_url import public_url_status

        status = public_url_status()
        return {
            "status": "ok",
            "public_base_url": status["public_base_url"],
            "public_url_source": status["source"],
            "currency": app.config.get("CURRENCY", "PKR"),
            "language": app.config.get("DEFAULT_LANGUAGE", "en"),
        }

    @app.get("/api/public/config")
    def public_config():
        from payments import payments_status
        from public_url import public_url_status

        status = public_url_status()
        return {
            "currency": app.config.get("CURRENCY", "PKR"),
            "language": app.config.get("DEFAULT_LANGUAGE", "en"),
            "payments": payments_status(),
            "public_base_url": status["public_base_url"],
            "public_url_source": status["source"],
            "public_url_hint": status.get("hint"),
        }

    return app
