from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ..config import settings

router = APIRouter()

ROBOTS = """User-agent: *

"""

FAKE_ENV = """# AeroCorp portal environment - HONEYTOKEN, every value below is fake
DATABASE_URL=postgresql://portal:FAKE-PASSWORD-DO-NOT-USE@db.internal.invalid:5432/portal
SECRET_KEY=FAKE-SECRET-KEY-DO-NOT-USE
SMTP_PASSWORD=FAKE-SMTP-PASSWORD-DO-NOT-USE
"""

FAKE_BACKUP = """-- AeroCorp portal backup - HONEYTOKEN, rows are fake
INSERT INTO users (username, password_hash, role) VALUES ('backup-admin', 'FAKE-HASH-DO-NOT-USE', 'admin');
INSERT INTO subscribers (email) VALUES ('person1@example.invalid'), ('person2@example.invalid');
"""


@router.get("/api/health")
def health():
    if settings.vuln_mode:
        return {"status": "ok", "mode": settings.mode_label}
    return {"status": "ok"}


#@router.get("/robots.txt", response_class=PlainTextResponse)
#def robots():
#    return ROBOTS


@router.get("/.env", response_class=PlainTextResponse)
def honeytoken_env():
    if not settings.vuln_mode:
        raise HTTPException(status_code=404, detail="Not found")
    return FAKE_ENV


@router.get("/backup/site-backup.sql", response_class=PlainTextResponse)
def honeytoken_backup():
    if not settings.vuln_mode:
        raise HTTPException(status_code=404, detail="Not found")
    return FAKE_BACKUP
