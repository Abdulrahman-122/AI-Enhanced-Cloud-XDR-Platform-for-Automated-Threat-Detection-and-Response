import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from .config import settings

_logger = logging.getLogger("aerocorp")
_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return
    _logger.setLevel(logging.INFO)
    _logger.propagate = False
    formatter = logging.Formatter("%(message)s")

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    _logger.addHandler(stream)

    try:
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.log_dir / "app.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)
    except OSError as exc:
        _logger.warning(json.dumps({"event": "log_file_unavailable", "error": str(exc)}))
    _configured = True


def log_event(event: str, **fields) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "app": "aerocorp-portal",
        "mode": settings.mode_label,
        "event": event,
        **fields,
    }
    _logger.info(json.dumps(record, default=str, ensure_ascii=False))
