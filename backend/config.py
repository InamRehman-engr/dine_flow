import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY") or SECRET_KEY
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://dineflow_admin:LocalSuperSecurePassword2026@localhost:5432/dineflow_prod",
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Optional static fallback. Prefer live request Host or ngrok API (see public_url.py).
    PUBLIC_BASE_URL = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
    NGROK_API_URL = (os.environ.get("NGROK_API_URL") or "http://host.docker.internal:4040").rstrip("/")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days
    RESET_TOKEN_HOURS = 2

    # JWT
    JWT_ACCESS_HOURS = float(os.environ.get("JWT_ACCESS_HOURS", "1"))
    JWT_REFRESH_DAYS = float(os.environ.get("JWT_REFRESH_DAYS", "14"))
    GUEST_SOCKET_HOURS = float(os.environ.get("GUEST_SOCKET_HOURS", "12"))
    REFRESH_COOKIE_NAME = "dineflow_refresh"

    # Locale
    DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "en")
    CURRENCY = os.environ.get("CURRENCY", "PKR")

    # Redis / Socket.IO
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # MinIO
    MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    MINIO_PUBLIC_URL = os.environ.get("MINIO_PUBLIC_URL", "http://localhost:9000").rstrip("/")
    MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "dineflow")
    MINIO_SECURE = os.environ.get("MINIO_SECURE", "0") in ("1", "true", "True")

    # Payments stub
    PAYMENTS_ENABLED = os.environ.get("PAYMENTS_ENABLED", "0") in ("1", "true", "True")
