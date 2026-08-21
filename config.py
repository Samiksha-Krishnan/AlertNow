import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Falls back to a local SQLite file if DATABASE_URL isn't set, so the app
    # still runs before you've wired up Neon. Point DATABASE_URL at your Neon
    # Postgres connection string (see .env.example) to use Neon for real.
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "alertnow.db"))
    # SQLAlchemy wants the "postgresql://" scheme (some providers hand out "postgres://").
    if _db_url.startswith("postgres://"):
        _db_url = "postgresql://" + _db_url[len("postgres://"):]
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8MB max upload

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
