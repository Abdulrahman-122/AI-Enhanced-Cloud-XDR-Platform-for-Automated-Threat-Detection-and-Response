import html
import re

from .config import settings

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text or "item"


def clean_text(value: str) -> str:
    """Strip control characters and surrounding whitespace (used by the hardened build)."""
    return _CONTROL_RE.sub("", value).strip()


def out_text(value: str | None) -> str:
    """Text destined for innerHTML on the client.

    Vulnerable build: returned untouched, so stored and reflected XSS work.
    Hardened build: HTML-escaped on the way out (output encoding).
    """
    value = value or ""
    return value if settings.vuln_mode else html.escape(value, quote=True)


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --------------------------------------------------------------------------- attack-pattern logging
# Payloads sent in POST bodies never reach NGINX's access log, so the application flags them itself.
# Each hit becomes a `suspicious_input` event that the Wazuh rules read. Patterns are deliberately
# simple: they catch textbook payloads (what Burp and sqlmap send first), not every possible attack.
from .logging_setup import log_event  # noqa: E402

SUSPICIOUS_PATTERNS = {
    "sqli": re.compile(r"(?i)(\bunion\b\s+(all\s+)?\bselect\b|'\s*or\s*'?\d*'?\s*=|\bor\s+1\s*=\s*1|;\s*drop\s+table|\bpg_sleep\s*\(|\bsleep\s*\(\s*\d|--\s*$|%27|'--)"),
    "xss": re.compile(r"(?i)(<\s*script|<\s*img[^>]*onerror|\bonerror\s*=|\bonload\s*=|javascript\s*:|<\s*svg|%3c\s*script)"),
    "traversal": re.compile(r"(\.\./|\.\.\\|%2e%2e|%252e|/etc/passwd|win\.ini|boot\.ini)", re.I),
}


def suspicious_kinds(*values) -> list[str]:
    text = " ".join(str(v) for v in values if v not in (None, ""))
    return [kind for kind, pattern in SUSPICIOUS_PATTERNS.items() if pattern.search(text)]


def flag_suspicious(path: str, client_ip: str, **fields) -> list[str]:
    """Log one `suspicious_input` event per request that contains an attack pattern. Returns the kinds found."""
    kinds = suspicious_kinds(*fields.values())
    if kinds:
        excerpt = {key: str(value)[:200] for key, value in fields.items()}
        log_event("suspicious_input", client_ip=client_ip, path=path, kinds=kinds, fields=excerpt)
    return kinds
