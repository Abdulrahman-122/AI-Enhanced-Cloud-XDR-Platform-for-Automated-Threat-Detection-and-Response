import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on", "vulnerable")


class Settings:
    def __init__(self) -> None:
        self.vuln_mode = _flag("VULN_MODE", True)
        self.mode_label = "vulnerable" if self.vuln_mode else "hardened"

        # Main database connection (read/write). Used by every normal route.
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://aerocorp_app:aerocorp_app@localhost:5432/aerocorp",
        )
        # Optional SELECT-only role used by the intentionally injectable search query,
        # so that SQL injection can read data but can never modify or drop your lab database.
        self.database_url_ro = os.getenv("DATABASE_URL_RO") or None

        secret = os.getenv("SECRET_KEY")
        if not secret:
            secret = "lab-only-secret" if self.vuln_mode else secrets.token_urlsafe(32)
        self.secret_key = secret
        self.token_ttl_seconds = int(os.getenv("TOKEN_TTL_SECONDS", "3600"))

        self.media_dir = Path(os.getenv("MEDIA_DIR", BASE_DIR / "media"))
        self.datasheet_dir = Path(os.getenv("DATASHEET_DIR", BASE_DIR / "datasheets"))
        self.log_dir = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
        self.admin_password = os.getenv("ADMIN_PASSWORD") or None


settings = Settings()
