import os
from dotenv import load_dotenv

load_dotenv()


def _require_env(key: str, fallback: str | None = None) -> str:
    """Return env var or raise a clear error if missing in production."""
    value = os.getenv(key, fallback)
    if value is None:
        raise RuntimeError(
            f"[CONFIG] Required environment variable '{key}' is not set. "
            "Copy .env.production.template → .env.production and fill in the value."
        )
    return value


class Config:
    """Base configuration — shared by all environments."""

    # ✅ FIXED: Use ONE stable secret key (from environment or fallback)
    # This MUST match app.secret_key in __init__.py create_app()
    SECRET_KEY = os.getenv('SECRET_KEY', 'carepoint-hospital-fixed-secret-key-do-not-change-2024')

    # ── Database ───────────────────────────────────────────────────────────────
    DB_USER     = os.getenv('DB_USER', 'hospital_user')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'Mysql')
    DB_HOST     = os.getenv('DB_HOST', 'localhost')
    DB_PORT     = os.getenv('DB_PORT', '3306')
    DB_NAME     = os.getenv('DB_NAME', 'hospital_db')

    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        '?charset=utf8mb4'
    )

    # Connection pool tuning:
    #   pool_recycle=280 → recycle before MySQL's default 8-hour wait_timeout
    #   pool_pre_ping    → detect stale connections before handing them to app
    #   pool_size=5      → persistent connections kept alive
    #   max_overflow=10  → extra burst connections allowed under load
    #   connect_timeout  → MySQL-specific TCP connect timeout (seconds)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'pool_size': 5,
        'max_overflow': 10,
        'connect_args': {
            'connect_timeout': 10,
        },
    }

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── AWS S3 (medical documents, lab reports, scans) ─────────────────────────
    AWS_ACCESS_KEY_ID     = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET         = os.getenv('AWS_S3_BUCKET')
    AWS_REGION            = os.getenv('AWS_REGION', 'ap-south-1')

    # ── Session ────────────────────────────────────────────────────────────────
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SECURE    = False  # overridden to True in ProductionConfig
    SESSION_COOKIE_SAMESITE  = 'Lax'  # Allow cookies in AJAX/fetch requests
    SESSION_COOKIE_DOMAIN    = None  # Fix session persistence across domains
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours


class DevelopmentConfig(Config):
    """Development — hot-reload, verbose errors.
    Connects to local MySQL.
    """
    DEBUG = True
    TESTING = False
    TEMPLATES_AUTO_RELOAD = True


class ProductionConfig(Config):
    """Production — AWS EC2 + AWS RDS MySQL.

    CRITICAL: SQLite is completely disabled.
    All env vars required by RDS must be present or the app refuses to start.
    """
    DEBUG = False
    TESTING = False

    # Force HTTPS-only session cookies when behind an SSL terminator (ALB/nginx)
    SESSION_COOKIE_SECURE = True

    # Validate that every required AWS / DB credential is present at startup
    @classmethod
    def validate(cls):
        required = ['SECRET_KEY', 'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise RuntimeError(
                f"[PRODUCTION CONFIG] Missing required environment variables: "
                f"{', '.join(missing)}\n"
                "Copy .env.production.template → .env.production and fill in all values."
            )

    # Tighter pool settings for RDS multi-AZ (more instance types available)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20,
        'connect_args': {
            'connect_timeout': 10,
        },
    }


class TestingConfig(Config):
    """Testing — in-memory SQLite (isolated, fast, no side effects)."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False}
    }
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}
