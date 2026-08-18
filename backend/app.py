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
import routes.websocket  # noqa: F401 — register socket handlers


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Trust nginx/ngrok proxy headers (HTTPS, host) so sessions and redirects work.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Admin often uses http://localhost while QR URLs use https ngrok.
    # Keep cookies working on both; set SESSION_COOKIE_SECURE=1 only if you force HTTPS-only admin.
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
    socketio.init_app(app, cors_allowed_origins="*", manage_session=False)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tenant_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(order_bp)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "public_base_url": app.config["PUBLIC_BASE_URL"]}

    return app
