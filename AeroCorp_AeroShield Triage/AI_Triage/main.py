"""AeroCorp XDR Assistant.

Watches Wazuh alerts from the indexer, classifies web attacks, explains them,
and provides a chat assistant that can answer questions and produce PDF/PPTX files.

Run:  uvicorn main:app --host 127.0.0.1 --port 9000
"""
import asyncio
import html
import ipaddress
import json
import os
import re
import sqlite3
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------------- configuration
INDEXER_URL = os.getenv("INDEXER_URL", "https://127.0.0.1:9200")
INDEXER_USER = os.getenv("INDEXER_USER", "admin")
INDEXER_PASS = os.getenv("WAZUH_INDEXER_PASS", "")
CA_CERT = os.getenv("WAZUH_CA_CERT") or False
ALERT_LEVEL_MIN = int(os.getenv("ALERT_LEVEL_MIN", "3"))
HIGH_LEVEL = 10
CRITICAL_LEVEL = 12
LOOKBACK_MINUTES = int(os.getenv("LOOKBACK_MINUTES", "60"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "15"))
PAGE_SIZE = 200
BATCH_SIZE = 10

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "nvidia/nemotron-3.5-bolt-e4b")

DB_PATH = os.getenv("XDR_DB", "xdr_monitor.db")
FILES_DIR = Path(os.getenv("FILES_DIR", "generated"))
FILES_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- database
SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY, ts TEXT, rule_id TEXT, rule_desc TEXT, level INTEGER,
    agent TEXT, srcip TEXT, full_log TEXT);
CREATE TABLE IF NOT EXISTS detections (
    alert_id TEXT PRIMARY KEY REFERENCES alerts(id), created TEXT, category TEXT,
    name TEXT, severity TEXT, level INTEGER, summary TEXT, details TEXT);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created TEXT, kind TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS chats (
    id TEXT PRIMARY KEY, title TEXT, created TEXT, pinned INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, created TEXT,
    role TEXT, text TEXT, file TEXT);
"""


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def migrate(c):
    """Add columns that older databases are missing (the schema grew over time)."""
    expected = {
        "chats": {"title": "TEXT", "created": "TEXT", "pinned": "INTEGER DEFAULT 0"},
        "chat_messages": {"chat_id": "TEXT", "created": "TEXT", "role": "TEXT", "text": "TEXT", "file": "TEXT"},
    }
    for table, cols in expected.items():
        have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
        for name, typ in cols.items():
            if name not in have:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")


def init_db():
    with db() as c:
        c.executescript(SCHEMA)
        migrate(c)
        c.execute("INSERT OR IGNORE INTO state(k, v) VALUES ('monitor', 'running')")
        c.execute("INSERT OR IGNORE INTO state(k, v) VALUES ('indexer', 'unknown')")


def now_utc():
    return datetime.now(timezone.utc)


def iso(d):
    return d.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def get_state(k, default=None):
    with db() as c:
        row = c.execute("SELECT v FROM state WHERE k = ?", (k,)).fetchone()
    return row["v"] if row else default


def set_state(k, v):
    with db() as c:
        c.execute(
            "INSERT INTO state(k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v",
            (k, v),
        )


def add_event(kind, text):
    with db() as c:
        c.execute(
            "INSERT INTO events(created, kind, text) VALUES (?, ?, ?)",
            (iso(now_utc()), kind, text),
        )


# ---------------------------------------------------------------- attack knowledge
# (category, name, Wazuh rule ids from local_rules.xml, keywords used as fallback)
CATEGORIES = [
    ("sqli", "SQL injection", {"100120", "100106", "100159"}, ["union select", "sql syntax", "' or '"]),
    ("xss", "Cross-site scripting (XSS)", {"100121"}, ["<script", "onerror=", "onload="]),
    ("traversal", "Path traversal", {"100122", "100158"}, ["../", "/etc/passwd", "traversal"]),
    ("enumeration", "ID enumeration", {"100102", "100131"}, []),
    ("scanning", "Scanner or brute-force activity", {"100153", "100154"}, ["nikto", "nmap", "sqlmap"]),
]

RESPONSES = {
    "sqli": {
        "summary": "Input contained SQL syntax (quotes, UNION, OR 1=1) that could change the database query.",
        "steps": [
            "Use parameterised queries (SQLAlchemy bind parameters) for every input that reaches the database.",
            "Hide database error details from users; return a generic error message.",
            "Give the application's database user only the permissions it needs, never superuser.",
            "Keep the WAF rule for quote and UNION patterns on while the code is fixed.",
        ],
        "links": [
            ["OWASP: SQL Injection", "https://owasp.org/www-community/attacks/SQL_Injection"],
            ["OWASP SQLi prevention cheat sheet",
             "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"],
        ],
    },
    "xss": {
        "summary": "Input contained HTML or JavaScript that could run in another visitor's browser.",
        "steps": [
            "Escape output in the template layer (React escapes by default; avoid dangerouslySetInnerHTML).",
            "Validate input on the server and reject tags in fields that should be plain text.",
            "Set a Content-Security-Policy header that blocks inline scripts.",
            "Set session cookies to HttpOnly and SameSite=Lax.",
        ],
        "links": [
            ["OWASP: Cross Site Scripting", "https://owasp.org/www-community/attacks/xss/"],
            ["OWASP XSS prevention cheat sheet",
             "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html"],
        ],
    },
    "traversal": {
        "summary": "A request tried to read files outside the intended folder (for example /etc/passwd).",
        "steps": [
            "Never build file paths from user input. Map IDs to known file names instead.",
            "Resolve the real path and check it is still inside the allowed folder.",
            "Run the web service as a user that cannot read system files.",
        ],
        "links": [
            ["OWASP: Path Traversal", "https://owasp.org/www-community/attacks/Path_Traversal"],
        ],
    },
    "enumeration": {
        "summary": "Someone is trying many object IDs to discover records they should not see.",
        "steps": [
            "Check on the server that the logged-in user owns the record before returning it.",
            "Use random identifiers (UUIDs) instead of sequential numbers where practical.",
            "Rate-limit lookups per IP and per account.",
        ],
        "links": [
            ["OWASP: Insecure Direct Object Reference prevention",
             "https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html"],
        ],
    },
    "scanning": {
        "summary": "Automated scanning or brute-force tooling is probing the site.",
        "steps": [
            "Rate-limit requests and add a short lockout after repeated failed logins.",
            "Hide server version banners (server_tokens off in NGINX).",
            "Block the scanner user-agent at NGINX while you review the logs.",
        ],
        "links": [
            ["MITRE ATT&CK: Active Scanning", "https://attack.mitre.org/techniques/T1595/"],
        ],
    },
}


def is_local(ip):
    try:
        a = ipaddress.ip_address(ip)
        return a.is_private or a.is_loopback
    except ValueError:
        return True


def steps_for(cat, ip):
    steps = list(RESPONSES[cat]["steps"])
    if ip and not is_local(ip):
        steps.insert(0, f"Block {ip} at the firewall while you investigate, for example: sudo ufw deny from {ip}")
    return steps


def links_for(cat, ip):
    links = [list(x) for x in RESPONSES[cat]["links"]]
    if ip and not is_local(ip):
        links.append([f"VirusTotal: {ip}", f"https://www.virustotal.com/gui/ip-address/{ip}"])
    return links


def classify(a):
    for cat, name, ids, _ in CATEGORIES:
        if a["rule_id"] in ids:
            return cat, name
    text = f"{a['rule_desc']} {a['full_log']}".lower()
    for cat, name, _, words in CATEGORIES:
        if any(w in text for w in words):
            return cat, name
    return None


def severity_for(level):
    if level >= CRITICAL_LEVEL:
        return "critical"
    if level >= HIGH_LEVEL:
        return "high"
    if level >= 6:
        return "medium"
    return "low"


# ---------------------------------------------------------------- Wazuh indexer
def describe(hit):
    src = hit.get("_source", {})
    rule = src.get("rule") or {}
    data = src.get("data") or {}
    return {
        "id": hit["_id"],
        "ts": src.get("@timestamp", ""),
        "rule_id": str(rule.get("id", "")),
        "rule_desc": rule.get("description", ""),
        "level": int(rule.get("level", 0) or 0),
        "agent": (src.get("agent") or {}).get("name", ""),
        "srcip": data.get("srcip") or data.get("client_ip") or "",
        "full_log": (src.get("full_log") or "")[:2000],
    }


async def fetch_alerts(since):
    body = {
        "size": PAGE_SIZE,
        "sort": [{"@timestamp": "asc"}],
        "query": {
            "bool": {
                "filter": [{"range": {"@timestamp": {"gte": since}}}],
                "should": [
                    {"range": {"rule.level": {"gte": ALERT_LEVEL_MIN}}},
                    {"wildcard": {"rule.id": "1001*"}},
                ],
                "minimum_should_match": 1,
            }
        },
    }
    async with httpx.AsyncClient(verify=CA_CERT, auth=(INDEXER_USER, INDEXER_PASS), timeout=20) as c:
        r = await c.post(f"{INDEXER_URL}/wazuh-alerts-*/_search", json=body)
        r.raise_for_status()
    return r.json()["hits"]["hits"]


def insert_alert(a):
    with db() as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO alerts(id, ts, rule_id, rule_desc, level, agent, srcip, full_log) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (a["id"], a["ts"], a["rule_id"], a["rule_desc"], a["level"],
             a["agent"], a["srcip"], a["full_log"]),
        )
    return cur.rowcount == 1


def record_detection(a, cat, name, summary):
    details = {"steps": steps_for(cat, a["srcip"]), "links": links_for(cat, a["srcip"])}
    with db() as c:
        c.execute(
            "INSERT OR REPLACE INTO detections(alert_id, created, category, name, severity, level, summary, details) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (a["id"], iso(now_utc()), cat, name, severity_for(a["level"]),
             a["level"], summary, json.dumps(details)),
        )


# ---------------------------------------------------------------- LLM
def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    starts = [i for i in (t.find("["), t.find("{")) if i != -1]
    return json.loads(t[min(starts):] if starts else t)


async def ask(messages, system, max_tokens=700):
    if not LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not set on the server.")
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json=payload,
        )
    if r.status_code >= 400:
        raise RuntimeError(f"LLM error {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"].strip()


async def explain_batch(found):
    """found: list of (alert, category, name). Returns {alert_id: summary}."""
    if not found or not LLM_API_KEY:
        return {}
    payload = [
        {"id": a["id"], "attack": name, "rule": a["rule_desc"], "level": a["level"],
         "source_ip": a["srcip"], "log": a["full_log"][:400]}
        for a, _, name in found[:BATCH_SIZE]
    ]
    prompt = (
        "For each alert, write one short plain-English sentence explaining what the attacker tried "
        "and why it matters. Reply only with a JSON list of objects with keys id and summary.\n"
        + json.dumps(payload)
    )
    try:
        text = await ask([{"role": "user", "content": prompt}],
                         "You are a SOC analyst. Output strict JSON only.", max_tokens=900)
        data = parse_json(text)
        return {d["id"]: d["summary"] for d in data if isinstance(d, dict) and "id" in d}
    except Exception:
        return {}


def context_block():
    with db() as c:
        rows = c.execute(
            "SELECT d.name, d.severity, d.summary, a.srcip, a.ts FROM detections d "
            "JOIN alerts a ON a.id = d.alert_id ORDER BY a.ts DESC LIMIT 8"
        ).fetchall()
    lines = [f"Monitor: {get_state('monitor')}. Indexer: {get_state('indexer')}."]
    if rows:
        lines += [f"- {r['ts']} {r['name']} ({r['severity']}) from {r['srcip'] or 'n/a'}: {r['summary']}"
                  for r in rows]
    else:
        lines.append("No attacks detected yet.")
    return "\n".join(lines)


def system_prompt():
    return (
        "You are the AeroCorp XDR security assistant for a student's security lab. "
        "Explain attacks, Wazuh alerts, Linux, Kubernetes, networking and security tools clearly and briefly. "
        "Put every shell command or config snippet in a fenced code block (```bash for commands, the language "
        "name for code). Keep explanations as plain text outside code blocks. "
        "Offensive testing help is only for the user's own lab systems.\n\n"
        "Current monitoring context:\n" + context_block()
    )


def make_title(text):
    t = re.sub(r"\s+", " ", text).strip()
    return (t[:48] + "…") if len(t) > 48 else (t or "New chat")


# ---------------------------------------------------------------- monitor loop
async def monitor_cycle():
    if get_state("monitor") != "running":
        return
    since = get_state("cursor") or iso(now_utc() - timedelta(minutes=LOOKBACK_MINUTES))
    try:
        hits = await fetch_alerts(since)
    except Exception as e:
        if get_state("indexer") != "error":
            add_event("system", f"Indexer unreachable ({e.__class__.__name__}). Retrying.")
        set_state("indexer", "error")
        return
    if get_state("indexer") != "ok":
        add_event("system", "Indexer connected. Watching for alerts.")
    set_state("indexer", "ok")
    set_state("last_poll", iso(now_utc()))
    if not hits:
        return

    fresh = [a for a in (describe(h) for h in hits) if insert_alert(a)]
    set_state("cursor", hits[-1]["_source"].get("@timestamp", since))
    set_state("last_alert", hits[-1]["_source"].get("@timestamp", ""))

    found = []
    for a in fresh:
        hit = classify(a)
        if hit:
            found.append((a, hit[0], hit[1]))
    if found:
        summaries = await explain_batch(found)
        for a, cat, name in found:
            summary = summaries.get(a["id"]) or RESPONSES[cat]["summary"]
            record_detection(a, cat, name, summary)
            add_event("attack", f"{name} from {a['srcip'] or 'unknown source'} on {a['agent'] or 'unknown agent'}")


async def poller():
    while True:
        try:
            await monitor_cycle()
        except Exception as e:
            add_event("system", f"Monitor error: {e}")
        await asyncio.sleep(POLL_SECONDS)


# ---------------------------------------------------------------- documents
def split_blocks(body):
    blocks = []
    for i, part in enumerate(body.split("```")):
        if i % 2:
            lines = part.split("\n")
            if len(lines) > 1 and re.fullmatch(r"[\w+#.-]*", lines[0].strip()):
                lines = lines[1:]
            code = "\n".join(lines).strip("\n")
            if code:
                blocks.append(("code", code))
        else:
            for para in re.split(r"\n\s*\n", part):
                if para.strip():
                    blocks.append(("text", para.strip()))
    return blocks


def build_pdf(path, title, body):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, title=title,
                            leftMargin=50, rightMargin=50, topMargin=50, bottomMargin=50)
    story = [Paragraph(html.escape(title), styles["Title"]), Spacer(1, 12)]
    for kind, chunk in split_blocks(body):
        if kind == "code":
            story.append(Preformatted(chunk, styles["Code"]))
        else:
            story.append(Paragraph(html.escape(chunk).replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 8))
    doc.build(story)


def build_pptx(path, title, body):
    from pptx import Presentation
    from pptx.util import Pt

    prs = Presentation()
    cover = prs.slides.add_slide(prs.slide_layouts[0])
    cover.shapes.title.text = title[:80]
    cover.placeholders[1].text = "AeroCorp XDR Assistant"

    items = []
    for kind, chunk in split_blocks(body):
        for line in chunk.split("\n"):
            if line.strip():
                items.append(("$ " + line.strip()) if kind == "code" else line.strip())
    for n, start in enumerate(range(0, len(items), 6), 1):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = title[:60] if n == 1 else f"{title[:50]} ({n})"
        tf = slide.placeholders[1].text_frame
        for i, line in enumerate(items[start:start + 6]):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = line[:180]
            p.font.size = Pt(18)
    prs.save(str(path))


def wants_file(text):
    t = text.lower()
    if not re.search(r"\b(make|create|generate|export|give|build|write)\b", t):
        return None
    if re.search(r"powerpoint|pptx|slide deck|slides|presentation", t):
        return "pptx"
    if "pdf" in t:
        return "pdf"
    return None


def make_document(kind, title, body):
    name = f"{uuid.uuid4().hex[:12]}.{kind}"
    path = FILES_DIR / name
    if kind == "pdf":
        build_pdf(path, title, body)
    else:
        build_pptx(path, title, body)
    return f"/files/{name}"


# ---------------------------------------------------------------- app
@asynccontextmanager
async def lifespan(_app):
    init_db()
    add_event("info", "Assistant started.")
    task = asyncio.create_task(poller())
    yield
    task.cancel()


app = FastAPI(title="AeroCorp XDR Assistant", lifespan=lifespan)
app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")


@app.exception_handler(sqlite3.Error)
async def db_error(_request, exc):
    return JSONResponse({"detail": f"Database error: {exc}"}, status_code=500)


class SettingsPatch(BaseModel):
    lab_name: str | None = None


@app.get("/api/settings")
def get_settings():
    return {"lab_name": get_state("lab_name", "AeroCorp Lab")}


@app.patch("/api/settings")
def patch_settings(body: SettingsPatch):
    if body.lab_name and body.lab_name.strip():
        set_state("lab_name", body.lab_name.strip()[:40])
    return get_settings()


class ChatPatch(BaseModel):
    title: str | None = None
    pinned: bool | None = None


class MessageIn(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


        "monitor": get_state("monitor"),
        "indexer": get_state("indexer"),
        "alerts": alerts,
        "attacks": attacks,
        "high": high,
        "last_alert": get_state("last_alert"),
        "last_poll": get_state("last_poll"),
    }


@app.post("/api/monitor/{action}")
def monitor_action(action: str):
    if action not in ("start", "pause"):
        raise HTTPException(404, "Unknown action")
    running = action == "start"
    set_state("monitor", "running" if running else "paused")
    add_event("info", "Monitoring started." if running else
              "Monitoring paused. Alerts will be checked when you start again.")
    return {"monitor": get_state("monitor")}

        "monitor": get_state("monitor"),
        "indexer": get_state("indexer"),
        "alerts": alerts,
        "attacks": attacks,
        "high": high,
        "last_alert": get_state("last_alert"),
        "last_poll": get_state("last_poll"),
    }


@app.post("/api/monitor/{action}")
def monitor_action(action: str):
    if action not in ("start", "pause"):
        raise HTTPException(404, "Unknown action")
    running = action == "start"
    set_state("monitor", "running" if running else "paused")
    add_event("info", "Monitoring started." if running else
              "Monitoring paused. Alerts will be checked when you start again.")
    return {"monitor": get_state("monitor")}


@app.get("/api/attacks")
def attacks():
    with db() as c:
        rows = c.execute(
            "SELECT d.alert_id, d.category, d.name, d.severity, d.level, d.summary, d.details, "
            "a.ts, a.rule_desc, a.srcip, a.agent FROM detections d JOIN alerts a ON a.id = d.alert_id "
            "ORDER BY a.ts DESC LIMIT 100"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["id"] = d.pop("alert_id")
        d["details"] = json.loads(d["details"] or "{}")
        out.append(d)
    return out


@app.get("/api/events")
def events(after: int = 0):
    with db() as c:
        rows = c.execute(
            "SELECT id, created, kind, text FROM events WHERE id > ? ORDER BY id DESC LIMIT 100",
            (after,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


@app.get("/api/chats")
def list_chats():
    with db() as c:
        rows = c.execute(
            "SELECT id, title, created, pinned FROM chats ORDER BY pinned DESC, created DESC"
        ).fetchall()
    return [{**dict(r), "pinned": bool(r["pinned"])} for r in rows]


@app.post("/api/chats")
def create_chat():
    cid = uuid.uuid4().hex
    with db() as c:
        c.execute("INSERT INTO chats(id, title, created, pinned) VALUES (?, ?, ?, 0)",
                  (cid, "New chat", iso(now_utc())))
    return {"id": cid, "title": "New chat"}
@app.get("/api/attacks")
def attacks():
    with db() as c:
        rows = c.execute(
            "SELECT d.alert_id, d.category, d.name, d.severity, d.level, d.summary, d.details, "
            "a.ts, a.rule_desc, a.srcip, a.agent FROM detections d JOIN alerts a ON a.id = d.alert_id "
            "ORDER BY a.ts DESC LIMIT 100"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["id"] = d.pop("alert_id")
        d["details"] = json.loads(d["details"] or "{}")
        out.append(d)
    return out


@app.get("/api/events")
def events(after: int = 0):
    with db() as c:
        rows = c.execute(
            "SELECT id, created, kind, text FROM events WHERE id > ? ORDER BY id DESC LIMIT 100",
            (after,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


@app.get("/api/chats")
def list_chats():
    with db() as c:
        rows = c.execute(
            "SELECT id, title, created, pinned FROM chats ORDER BY pinned DESC, created DESC"
        ).fetchall()
    return [{**dict(r), "pinned": bool(r["pinned"])} for r in rows]


@app.post("/api/chats")
def create_chat():
    cid = uuid.uuid4().hex
    with db() as c:
        c.execute("INSERT INTO chats(id, title, created, pinned) VALUES (?, ?, ?, 0)",
                  (cid, "New chat", iso(now_utc())))
    return {"id": cid, "title": "New chat"}@app.get("/api/status")
def status():
    with db() as c:
        alerts = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        attacks = c.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
        high = c.execute(
            "SELECT COUNT(*) FROM detections WHERE severity IN ('high', 'critical')"
        ).fetchone()[0]
    return {
        "monitor": get_state("monitor"),
        "indexer": get_state("indexer"),
        "alerts": alerts,
        "attacks": attacks,
        "high": high,
        "last_alert": get_state("last_alert"),
        "last_poll": get_state("last_poll"),
    }


@app.post("/api/monitor/{action}")
def monitor_action(action: str):
    if action not in ("start", "pause"):
        raise HTTPException(404, "Unknown action")
    running = action == "start"
    set_state("monitor", "running" if running else "paused")
    add_event("info", "Monitoring started." if running else
              "Monitoring paused. Alerts will be checked when you start again.")
    return {"monitor": get_state("monitor")}


@app.get("/api/attacks")
def attacks():
    with db() as c:
        rows = c.execute(
            "SELECT d.alert_id, d.category, d.name, d.severity, d.level, d.summary, d.details, "
            "a.ts, a.rule_desc, a.srcip, a.agent FROM detections d JOIN alerts a ON a.id = d.alert_id "
            "ORDER BY a.ts DESC LIMIT 100"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["id"] = d.pop("alert_id")
        d["details"] = json.loads(d["details"] or "{}")
        out.append(d)
    return out


@app.get("/api/events")
def events(after: int = 0):
    with db() as c:
        rows = c.execute(
            "SELECT id, created, kind, text FROM events WHERE id > ? ORDER BY id DESC LIMIT 100",
            (after,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


@app.get("/api/chats")
def list_chats():
    with db() as c:
        rows = c.execute(
            "SELECT id, title, created, pinned FROM chats ORDER BY pinned DESC, created DESC"
        ).fetchall()
    return [{**dict(r), "pinned": bool(r["pinned"])} for r in rows]


@app.post("/api/chats")
def create_chat():
    cid = uuid.uuid4().hex
    with db() as c:
        c.execute("INSERT INTO chats(id, title, created, pinned) VALUES (?, ?, ?, 0)",
                  (cid, "New chat", iso(now_utc())))
    return {"id": cid, "title": "New chat"}

@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str):
    with db() as c:
        chat = c.execute("SELECT id, title, created, pinned FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat:
            raise HTTPException(404, "Chat not found")
        msgs = c.execute(
            "SELECT id, created, role, text, file FROM chat_messages WHERE chat_id = ? ORDER BY id",
            (chat_id,),
        ).fetchall()
    return {**dict(chat), "pinned": bool(chat["pinned"]), "messages": [dict(m) for m in msgs]}


@app.patch("/api/chats/{chat_id}")
def patch_chat(chat_id: str, body: ChatPatch):
    with db() as c:
        if not c.execute("SELECT 1 FROM chats WHERE id = ?", (chat_id,)).fetchone():
            raise HTTPException(404, "Chat not found")
        if body.title is not None and body.title.strip():
            c.execute("UPDATE chats SET title = ? WHERE id = ?", (body.title.strip()[:80], chat_id))
        if body.pinned is not None:
            c.execute("UPDATE chats SET pinned = ? WHERE id = ?", (1 if body.pinned else 0, chat_id))
    return {"ok": True}


@app.delete("/api/chats/{chat_id}")
def delete_chat(chat_id: str):
    with db() as c:
        c.execute("DELETE FROM chat_messages WHERE chat_id = ?", (chat_id,))
        c.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    return {"ok": True}


@app.post("/api/chats/{chat_id}/messages")
async def send_message(chat_id: str, body: MessageIn):
    text = body.message.strip()
    if not text:
        raise HTTPException(400, "Empty message")
    with db() as c:
        chat = c.execute("SELECT title FROM chats WHERE id = ?", (chat_id,)).fetchone()
        if not chat:
            raise HTTPException(404, "Chat not found")
        history = c.execute(
            "SELECT role, text FROM chat_messages WHERE chat_id = ? ORDER BY id DESC LIMIT 12",
            (chat_id,),
        ).fetchall()
        c.execute(
            "INSERT INTO chat_messages(chat_id, created, role, text, file) VALUES (?, ?, 'user', ?, NULL)",
            (chat_id, iso(now_utc()), text),
        )
        if chat["title"] == "New chat":
            c.execute("UPDATE chats SET title = ? WHERE id = ?", (make_title(text), chat_id))

    messages = [{"role": r["role"], "content": r["text"]} for r in reversed(history)]
    messages.append({"role": "user", "content": text})
    try:
        answer = await ask(messages, system_prompt(), max_tokens=1200)
    except Exception as e:
        raise HTTPException(502, str(e) or e.__class__.__name__)

    file_url = None
    kind = wants_file(text)
    if kind:
        file_url = make_document(kind, make_title(text), answer)
    with db() as c:
        c.execute(
            "INSERT INTO chat_messages(chat_id, created, role, text, file) VALUES (?, ?, 'assistant', ?, ?)",
            (chat_id, iso(now_utc()), answer, file_url),
        )
    return {"role": "assistant", "text": answer, "file": file_url}


# ---------------------------------------------------------------- page
PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AeroCorp XDR</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script>try{var t=localStorage.getItem("xdr-theme");if(t)document.documentElement.dataset.theme=t;}catch(e){}</script>
<style>
:root{
  --bg:#f6f6f1;--side:#efefe8;--card:#ffffff;--card2:#f1f1ea;--line:#e2e2d8;
  --text:#1d2019;--muted:#6f7266;
  --accent:#d8f36e;--accent-hover:#cbe75a;--accent-ink:#1b2208;--accent-soft:#eef9c9;
  --ok:#2f7d32;--ok-soft:#e3f4d8;--danger:#b42318;--danger-soft:#fdeceb;
  --warn:#9a6700;--warn-soft:#fbf1d3;--info:#1d6f8c;
  --shadow:0 1px 2px rgba(20,25,10,.05),0 10px 26px -14px rgba(20,25,10,.16);
  --code:#1f2319;--code-text:#e9efd9;
  --font:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#101210;--side:#161915;--card:#1a1e18;--card2:#20251d;--line:#2b3127;
    --text:#eef1e8;--muted:#9aa292;
    --accent:#d8f36e;--accent-hover:#e4f98a;--accent-ink:#172006;--accent-soft:#2a3514;
    --ok:#8fd694;--ok-soft:#1d2f1e;--danger:#ff8a80;--danger-soft:#3a1b19;
    --warn:#f2c46b;--warn-soft:#352b12;--info:#7fd3ea;
    --shadow:0 12px 32px -18px rgba(0,0,0,.8);--code:#0b0d09;--code-text:#e4ecd0;
  }
}
:root[data-theme="dark"]{
  --bg:#101210;--side:#161915;--card:#1a1e18;--card2:#20251d;--line:#2b3127;
  --text:#eef1e8;--muted:#9aa292;
  --accent:#d8f36e;--accent-hover:#e4f98a;--accent-ink:#172006;--accent-soft:#2a3514;
  --ok:#8fd694;--ok-soft:#1d2f1e;--danger:#ff8a80;--danger-soft:#3a1b19;
  --warn:#f2c46b;--warn-soft:#352b12;--info:#7fd3ea;
  --shadow:0 12px 32px -18px rgba(0,0,0,.8);--code:#0b0d09;--code-text:#e4ecd0;
}
*{box-sizing:border-box}
[hidden]{display:none!important}
html,body{height:100%}
body{margin:0;display:grid;grid-template-columns:268px minmax(0,1fr);background:var(--bg);color:var(--text);font:15px/1.55 var(--font)}
body.collapsed{grid-template-columns:minmax(0,1fr)}
body.collapsed .side{display:none}
button,input,textarea{font:inherit;color:inherit}
button{cursor:pointer}
.ic{width:18px;height:18px;flex:none;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.ic.sm{width:15px;height:15px}

/* ---- sidebar ---- */
.side{background:var(--side);border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0;padding:14px 12px 12px;transition:transform .25s}
.side-head{display:flex;align-items:center;justify-content:space-between;padding:2px 6px 12px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:19px;letter-spacing:-.3px}
.brand .logo{width:30px;height:30px;border-radius:9px;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center}
.brand sup{font-size:10px;font-weight:700;color:var(--muted);margin-left:3px;letter-spacing:.6px}
.ghostbtn{width:34px;height:34px;border-radius:10px;border:0;background:transparent;color:var(--muted);display:grid;place-items:center}
.ghostbtn:hover{background:var(--card2);color:var(--text)}
.newchat{display:flex;align-items:center;gap:9px;width:100%;border:0;border-radius:12px;padding:11px 14px;background:var(--accent);color:var(--accent-ink);font-weight:600;font-size:15px}
.newchat:hover{background:var(--accent-hover)}
.newchat kbd{margin-left:auto;font:500 12px var(--mono);opacity:.7}
.search{display:flex;align-items:center;gap:9px;padding:9px 12px;border-radius:12px;color:var(--muted);margin-top:8px}
.search input{border:0;outline:0;background:transparent;width:100%;font-size:14.5px}
.search:focus-within{background:var(--card);box-shadow:inset 0 0 0 1px var(--line)}
.label{font-size:12.5px;color:var(--muted);font-weight:600;padding:16px 10px 6px}
.nav{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:10px;border:0;background:transparent;text-align:left;width:100%;font-weight:500}
.nav:hover{background:var(--card2)}
.nav.on{background:var(--card);box-shadow:var(--shadow)}
.nav .count{margin-left:auto;font-size:12px;color:var(--muted);font-weight:600}
#chatlist{overflow:auto;flex:1;min-height:0;margin:0 -4px;padding:0 4px}
.grp{font-size:12.5px;color:var(--muted);font-weight:600;padding:14px 10px 6px}
.chat{display:flex;align-items:center;gap:8px;padding:9px 8px 9px 10px;border-radius:10px;cursor:pointer}
.chat:hover{background:var(--card2)}
.chat.on{background:var(--card);box-shadow:var(--shadow)}
.chat .t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14.5px}
.chat .ic{color:var(--muted)}
.chat .acts{display:flex;gap:2px;opacity:0;transition:opacity .15s}
.chat:hover .acts,.chat.on .acts,.chat:focus-within .acts{opacity:1}
@media (hover:none){.chat .acts{opacity:1}}
.tiny{width:26px;height:26px;border-radius:8px;border:0;background:transparent;color:var(--muted);display:grid;place-items:center}
.tiny:hover{background:var(--card);color:var(--text)}
.tiny.on{color:var(--text);background:var(--accent-soft)}
.tiny.danger:hover{color:var(--danger)}
.empty-side{color:var(--muted);font-size:13.5px;padding:10px}
.promo{position:relative;margin-top:10px;border-radius:16px;padding:14px;background:var(--card);border:1px solid var(--line)}
.promo b{display:block;font-size:14.5px}
.promo p{margin:3px 0 10px;color:var(--muted);font-size:13px;line-height:1.45}
.promo-x{position:absolute;top:8px;right:8px;width:26px;height:26px}
.userrow{display:flex;align-items:center;gap:10px;padding:12px 6px 2px;margin-top:8px;border-top:1px solid var(--line)}
.userrow .av{width:32px;height:32px;border-radius:50%;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center;font-weight:700;font-size:13px}
.userrow .tiny{margin-left:auto}
.userrow small{display:block;color:var(--muted);font-size:12.5px}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:12px;padding:9px 14px;font-weight:600;font-size:14.5px;background:var(--accent);color:var(--accent-ink)}
.btn:hover{background:var(--accent-hover)}
.btn.ghost{background:transparent;color:var(--text);border:1px solid var(--line)}
.btn.ghost:hover{border-color:var(--muted);background:transparent}
.btn:disabled{opacity:.4;cursor:not-allowed}

/* ---- main ---- */
.main{display:flex;flex-direction:column;min-width:0;min-height:0}
.topbar{display:flex;align-items:center;gap:12px;padding:12px 22px;border-bottom:1px solid var(--line);background:var(--bg);min-height:60px}
.menu-btn{display:none}
.model{display:flex;align-items:center;gap:9px;font-weight:600;font-size:15.5px;min-width:0}
.model .tag{font-size:12px;font-weight:600;padding:3px 9px;border-radius:999px;background:var(--accent-soft);white-space:nowrap}
.spacer{flex:1}
.pill{display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:500;color:var(--muted);padding:6px 10px;border-radius:999px;white-space:nowrap}
.pill .ic{width:15px;height:15px}
.dot{width:8px;height:8px;border-radius:50%;background:currentColor;flex:none}
.pill.ok{color:var(--ok)}
.pill.warn{color:var(--warn)}
.pill.bad{color:var(--danger)}
.pill.ok .dot{animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(47,125,50,.45)}70%{box-shadow:0 0 0 7px rgba(47,125,50,0)}100%{box-shadow:0 0 0 0 rgba(47,125,50,0)}}
.views{flex:1;min-height:0;display:flex;flex-direction:column}

/* ask view */
.thread{flex:1;overflow:auto;padding:28px 22px 12px;display:flex;flex-direction:column;gap:22px;min-height:0}
.welcome{margin:auto;max-width:960px;width:100%;text-align:center;display:flex;flex-direction:column;align-items:center}
.welcome .big{width:56px;height:56px;border-radius:18px;background:var(--accent-soft);display:grid;place-items:center}
.welcome .big .ic{width:24px;height:24px}
.kicker{margin-top:22px;font-size:11.5px;letter-spacing:1.6px;text-transform:uppercase;color:var(--muted);font-weight:600}
.welcome h1{font-size:clamp(30px,4.2vw,44px);letter-spacing:-1px;margin:8px 0 0;font-weight:600}
.welcome .lead{margin:8px 0 0;color:var(--muted);font-size:16.5px}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:34px;width:100%;text-align:left}
.card{position:relative;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px;color:var(--text);box-shadow:var(--shadow);transition:border-color .15s,transform .1s}
.card:hover{border-color:var(--muted)}
.card:active{transform:translateY(1px)}
.card .arrow{position:absolute;right:16px;top:16px;color:var(--muted)}
.card .tile{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;margin-bottom:22px}
.card h3{margin:0 0 6px;font-size:15.5px;font-weight:600}
.card p{margin:0;color:var(--muted);font-size:13.5px;line-height:1.5}
.t-alert{background:var(--danger-soft);color:var(--danger)}
.t-cmd{background:var(--accent-soft);color:var(--text)}
.t-file{background:var(--warn-soft);color:var(--warn)}
.not-sure{margin-top:22px;color:var(--muted);font-size:13.5px}

.turn{max-width:860px;width:100%;margin:0 auto;display:flex;gap:12px;align-items:flex-start}
.turn.user{justify-content:flex-end}
.turn.user .bubble{background:var(--accent-soft);border-radius:18px 18px 4px 18px;padding:11px 16px;max-width:78%;white-space:pre-wrap}
.turn .av{width:30px;height:30px;border-radius:10px;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center;flex:none;margin-top:2px}
.turn .body{min-width:0;flex:1;line-height:1.65}
.turn .body p{margin:0 0 10px;white-space:pre-wrap}
.turn .body p:last-child{margin-bottom:0}
.turn.error .body{color:var(--danger);background:var(--danger-soft);padding:10px 14px;border-radius:12px}
code{background:var(--card2);border:1px solid var(--line);border-radius:6px;padding:1px 6px;font-family:var(--mono);font-size:.88em}
.code{margin:12px 0;border-radius:14px;overflow:hidden;background:var(--code);border:1px solid var(--line)}
.codebar{display:flex;align-items:center;justify-content:space-between;padding:7px 8px 7px 13px;color:#a8b39a;font-size:12px;font-weight:600}
.codebar .lbl{display:flex;align-items:center;gap:7px}
.codebar .lbl.cmd{color:var(--accent)}
.codebar button{display:flex;align-items:center;gap:6px;background:transparent;border:1px solid rgba(255,255,255,.14);color:inherit;border-radius:9px;padding:4px 9px;font:600 12px var(--font)}
.codebar button:hover{border-color:var(--accent);color:var(--accent)}
.code pre{margin:0;padding:12px 15px;overflow:auto;color:var(--code-text);font:13px/1.6 var(--mono)}
.filelink{display:inline-flex;align-items:center;gap:8px;margin-top:10px;background:var(--accent);color:var(--accent-ink);padding:9px 14px;border-radius:12px;text-decoration:none;font-weight:600}
.dots{display:inline-flex;gap:5px;padding:8px 0}
.dots i{width:7px;height:7px;border-radius:50%;background:var(--muted);animation:blink 1.2s infinite}
.dots i:nth-child(2){animation-delay:.2s}
.dots i:nth-child(3){animation-delay:.4s}
@keyframes blink{0%,80%,100%{opacity:.25}40%{opacity:1}}
.composer{padding:8px 22px 16px;background:var(--bg)}
.composer-box{max-width:880px;margin:0 auto;background:var(--card);border:1px solid var(--line);border-radius:22px;padding:14px 14px 10px;box-shadow:var(--shadow)}
.composer-box:focus-within{border-color:var(--muted)}
#q{width:100%;border:0;outline:0;resize:none;background:transparent;font-size:15.5px;line-height:1.5;min-height:26px;max-height:180px;padding:4px 4px 6px;display:block}
#q::placeholder{color:var(--muted)}
.toolbar{display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap}
.chipbtn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:transparent;border-radius:999px;padding:6px 11px;font-size:13px;color:var(--muted)}
.chipbtn:hover{color:var(--text);border-color:var(--muted)}
.send{margin-left:auto;width:40px;height:40px;border-radius:13px;border:0;background:var(--accent);color:var(--accent-ink);display:grid;place-items:center}
.send:hover{background:var(--accent-hover)}
.send:disabled{opacity:.4}
.note{text-align:center;color:var(--muted);font-size:12.5px;margin:10px auto 0}

/* monitor view */
.mon{flex:1;overflow:auto;padding:22px;display:flex;flex-direction:column;gap:16px;max-width:1280px;width:100%;margin:0 auto}
.mhero{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:18px 20px;box-shadow:var(--shadow)}
.mhero-left{display:flex;align-items:center;gap:14px}
.orb{width:48px;height:48px;border-radius:15px;display:grid;place-items:center;background:var(--ok-soft);color:var(--ok)}
.orb.paused{background:var(--warn-soft);color:var(--warn)}
.mhero h2{margin:0;font-size:20px;font-weight:600;letter-spacing:-.3px}
.mhero p{margin:3px 0 0;color:var(--muted);font-size:14px}
.mhero-actions{display:flex;gap:10px}
.stats{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px;display:flex;flex-direction:column;gap:12px;box-shadow:var(--shadow);min-width:0}
.stat .lbl{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:12.5px;font-weight:500}
.stat .ico{width:26px;height:26px;border-radius:8px;display:grid;place-items:center;background:var(--card2)}
.stat .ico .ic{width:15px;height:15px}
.stat b{font-size:24px;font-weight:600;letter-spacing:-.5px;line-height:1.1}
.stat b.txt{font-size:13.5px;font-weight:600;letter-spacing:0;word-break:break-word;line-height:1.35}
.stat.danger .ico{background:var(--danger-soft);color:var(--danger)}
.stat.danger b{color:var(--danger)}
.cols{display:grid;grid-template-columns:1.35fr 1fr;gap:16px;align-items:start}
.panel{background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow);display:flex;flex-direction:column;min-width:0}
.panel-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--line)}
.panel-head h3{margin:0;font-size:15.5px;font-weight:600;display:flex;align-items:center;gap:9px}
.panel-body{padding:14px 16px;overflow:auto;max-height:68vh}
.count{font-size:12px;font-weight:600;background:var(--card2);color:var(--muted);border-radius:999px;padding:3px 10px}
.empty{color:var(--muted);font-size:14px;margin:6px 2px}
.attack{position:relative;border:1px solid var(--line);background:var(--card2);border-radius:16px;padding:14px 16px 14px 20px;margin-bottom:12px}
.attack::before{content:"";position:absolute;left:0;top:12px;bottom:12px;width:4px;border-radius:4px;background:var(--warn)}
.attack.high,.attack.critical{background:var(--danger-soft);border-color:transparent}
.attack.high::before,.attack.critical::before{background:var(--danger)}
.attack-head{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.attack-title{display:flex;align-items:center;gap:8px;font-weight:600;font-size:15.5px}
.attack.high .attack-title,.attack.critical .attack-title{color:var(--danger)}
.sevtag{font-size:11px;font-weight:700;letter-spacing:.6px;text-transform:uppercase;padding:4px 10px;border-radius:999px;background:var(--warn-soft);color:var(--warn)}
.attack.high .sevtag{background:var(--danger);color:#fff}
.attack.critical .sevtag{background:#7f1d1d;color:#fff}
.meta{display:flex;align-items:center;gap:6px;flex-wrap:wrap;color:var(--muted);font-size:12.5px;margin-top:6px}
.attack p{margin:10px 0 0;line-height:1.55}
.steps-title{margin:14px 0 2px;font-size:12px;font-weight:600;color:var(--muted)}
.attack ol{margin:0;padding:0;list-style:none;counter-reset:s}
.attack li{counter-increment:s;display:flex;gap:10px;margin:7px 0;line-height:1.5}
.attack li::before{content:counter(s);flex:none;width:22px;height:22px;border-radius:7px;background:var(--card);border:1px solid var(--line);display:grid;place-items:center;font:600 12px var(--mono);color:var(--text)}
.links{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.links a{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;color:var(--info);text-decoration:none;background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 11px}
.links a:hover{border-color:var(--info)}
.ev{display:grid;grid-template-columns:30px 1fr;gap:12px;padding:11px;border-radius:14px;background:var(--card2);margin-bottom:10px}
.ev .ico-wrap{width:30px;height:30px;border-radius:10px;display:grid;place-items:center;background:var(--card);color:var(--info)}
.ev.k-attack .ico-wrap{color:var(--danger)}
.ev.k-system .ico-wrap{color:var(--warn)}
.ev .meta{margin:0 0 3px;font-size:11.5px}
.ev .body{white-space:pre-wrap;line-height:1.45;font-size:14px}

/* ---- responsive ---- */
@media (max-width:1100px){
  .stats{grid-template-columns:repeat(3,minmax(0,1fr))}
  .cols{grid-template-columns:1fr}
  .cards{grid-template-columns:1fr 1fr}
}
@media (max-width:820px){
  body{grid-template-columns:minmax(0,1fr);height:100%}
  .side{position:fixed;top:0;bottom:0;left:0;width:280px;z-index:20;transform:translateX(-105%);box-shadow:var(--shadow)}
  body.nav-open .side{transform:none}
  .menu-btn{display:grid}
  .thread,.mon{padding:18px 16px}
  .composer{padding:8px 16px 14px}
  .cards{grid-template-columns:1fr}
  .stats{grid-template-columns:repeat(2,minmax(0,1fr))}
  .turn.user .bubble{max-width:92%}
  .pill.hide-sm{display:none}
  .mhero{align-items:flex-start}
}
</style>
</head>
<body>

<aside class="side" id="side">
  <div class="side-head">
    <div class="brand"><div class="logo" data-ic="radar"></div><div>AeroCorp<sup>XDR</sup></div></div>
  </div>
  <button class="newchat" id="btn-new">New chat <kbd>Ctrl K</kbd></button>
  <label class="search" data-ic="search"><input id="search" placeholder="Search chats" autocomplete="off"></label>

  <div class="label">Explore</div>
  <button class="nav on" id="nav-ask" data-ic="chat">Assistant</button>
  <button class="nav" id="nav-monitor" data-ic="activity">Live monitor <span class="count" id="nav-alerts">0</span></button>
  <button class="nav" id="nav-attacks" data-ic="target">Attacks <span class="count" id="nav-attack-count">0</span></button>

  <div id="chatlist" style="margin-top:4px"></div>

  <div class="promo" id="promo">
    <button class="tiny promo-x" id="promo-x" aria-label="Hide this card" title="Hide this card" data-ic="x"></button>
    <b id="promo-title">Monitoring is live</b>
    <p id="promo-sub">Every new Wazuh alert is checked automatically.</p>
    <button class="btn ghost" id="promo-btn" style="width:100%">Open live monitor</button>
  </div>
  <div class="userrow">
    <div class="av" id="lab-av">AC</div>
    <div><b id="lab-name">AeroCorp Lab</b><small>Local model · Free</small></div>
    <button class="tiny" id="lab-edit" aria-label="Rename lab" title="Rename lab" data-ic="pencil"></button>
  </div>
</aside>

<main class="main">
  <header class="topbar">
    <button class="ghostbtn" id="collapse-btn" title="Show or hide sidebar" aria-label="Show or hide sidebar" data-ic="panel"></button>
    <div class="model"><span>AeroCorp Assistant</span><span class="tag">Nemotron</span></div>
    <div class="spacer"></div>
    <span class="pill" id="pill-monitor"><i class="dot"></i><span>…</span></span>
    <span class="pill hide-sm" id="pill-indexer"><i class="dot"></i><span>…</span></span>
    <span class="pill hide-sm" data-ic="lock">Private lab</span>
    <button class="ghostbtn" id="theme-btn" aria-label="Switch light and dark mode" title="Switch light and dark mode"></button>
  </header>

  <!-- Assistant -->
  <section class="views" id="view-ask">
    <div class="thread" id="messages"></div>
    <div class="composer">
      <div class="composer-box">
        <textarea id="q" rows="1" placeholder="Ask about attacks, commands, Linux, Kubernetes, XDR, or anything else…"></textarea>
        <div class="toolbar">
          <button class="chipbtn" type="button" data-prompt="What attacks happened in the last hour, and how do I stop them?" data-ic="target">Attacks</button>
          <button class="chipbtn" type="button" data-prompt="Show the commands to check the Wazuh indexer from a Linux VM" data-ic="terminal">Commands</button>
          <button class="chipbtn" type="button" data-prompt="Make a PDF report about the attacks so far" data-ic="file">PDF report</button>
          <button class="chipbtn" type="button" data-prompt="Make a PowerPoint that explains how XDR works" data-ic="file">PowerPoint</button>
          <button class="send" id="send" type="button" aria-label="Send" data-ic="send"></button>
        </div>
      </div>
      <p class="note">The assistant can make mistakes. Check commands before you run them on a real system.</p>
    </div>
  </section>

  <!-- Live monitor -->
  <section class="views mon" id="view-monitor" hidden>
    <div class="mhero">
      <div class="mhero-left">
        <div class="orb" id="orb"></div>
        <div>
          <h2 id="hero-title">Monitoring</h2>
          <p id="hero-sub">Loading status…</p>
        </div>
      </div>
      <div class="mhero-actions">
        <button class="btn" id="btn-start" data-ic="play">Start</button>
        <button class="btn ghost" id="btn-pause" data-ic="pause">Pause</button>
      </div>
    </div>

    <div class="stats">
      <div class="stat"><div class="lbl"><span class="ico" data-ic="layers"></span>Alerts checked</div><b id="stat-alerts">0</b></div>
      <div class="stat"><div class="lbl"><span class="ico" data-ic="target"></span>Attacks</div><b id="stat-attacks">0</b></div>
      <div class="stat danger"><div class="lbl"><span class="ico" data-ic="alert"></span>High or critical</div><b id="stat-high">0</b></div>
      <div class="stat"><div class="lbl"><span class="ico" data-ic="eye"></span>Last alert</div><b class="txt" id="stat-latest">none</b></div>
      <div class="stat"><div class="lbl"><span class="ico" data-ic="clock"></span>Last check</div><b class="txt" id="stat-poll">never</b></div>
      <div class="stat"><div class="lbl"><span class="ico" data-ic="server"></span>Indexer</div><b class="txt" id="stat-indexer">unknown</b></div>
    </div>

    <div class="cols">
      <section class="panel" id="panel-attacks">
        <div class="panel-head"><h3><span data-ic="target"></span>Attacks</h3><span class="count" id="attack-count">0</span></div>
        <div class="panel-body" id="attacks"></div>
      </section>
      <section class="panel">
        <div class="panel-head"><h3><span data-ic="activity"></span>Activity</h3></div>
        <div class="panel-body" id="events"></div>
      </section>
    </div>
  </section>
</main>

<script>
const $ = id => document.getElementById(id);

const ICONS = {
  radar: '<circle cx="12" cy="12" r="9"/><path d="M12 12l6.5-5.5"/><circle cx="12" cy="12" r="2.5"/>',
  activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
  chat: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  alert: '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  play: '<polygon points="7 4 20 12 7 20 7 4"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  pin: '<line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14l-1.5-6V4h-11v7z"/>',
  pencil: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',
  server: '<rect x="2" y="3" width="20" height="8" rx="2"/><rect x="2" y="13" width="20" height="8" rx="2"/><line x1="6" y1="7" x2="6.01" y2="7"/><line x1="6" y1="17" x2="6.01" y2="17"/>',
  clock: '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15.5 14"/>',
  send: '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
  sparkle: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 17l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
  layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
  eye: '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7"/>',
  terminal: '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
  code: '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
  search: '<circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  panel: '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/>',
  lock: '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  menu: '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  arrow: '<line x1="7" y1="17" x2="17" y2="7"/><polyline points="7 7 17 7 17 17"/>'
};

function icon(name, cls = "") {
  const t = document.createElement("template");
  t.innerHTML = `<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
  return t.content.firstElementChild;
}
function paintIcons() {
  document.querySelectorAll("[data-ic]").forEach(el => {
    if (!el.querySelector(":scope > svg")) el.prepend(icon(el.dataset.ic));
  });
}
function h(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function iconBtn(cls, name, title, onClick) {
  const b = h("button", cls);
  b.title = title;
  b.setAttribute("aria-label", title);
  b.append(icon(name, "sm"));
  b.onclick = onClick;
  return b;
}
async function api(url, opts = {}) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    const j = await r.json().catch(() => ({}));
    throw new Error(j.detail || ("HTTP " + r.status));
  }
  return r.json();
}

// ---- time: stored in UTC, shown in Cairo time ----
const TZ = "Africa/Cairo";
const fullFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: TZ, day: "2-digit", month: "short", year: "numeric",
  hour: "2-digit", minute: "2-digit", hour12: false
});
const dayFmt = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" });

function parseTs(s) {
  if (!s) return null;
  let t = String(s).trim().replace(" ", "T");
  t = t.replace(/([+-]\d{2})(\d{2})$/, "$1:$2");   // +0000 -> +00:00
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(t)) t += "Z";   // no zone means UTC
  const d = new Date(t);
  return isNaN(d) ? null : d;
}
function fmtTime(s) {
  const d = parseTs(s);
  return d ? fullFmt.format(d) + " Cairo" : "";
}
function dayKey(d) {
  return d ? dayFmt.format(d) : "";
}

// ---- theme ----
function isDark() {
  const t = document.documentElement.dataset.theme;
  return t ? t === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}
function paintTheme() {
  $("theme-btn").replaceChildren(icon(isDark() ? "sun" : "moon"));
}
$("theme-btn").onclick = () => {
  const next = isDark() ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("xdr-theme", next); } catch (e) {}
  paintTheme();
};

// ---- navigation ----
function show(view) {
  $("view-ask").hidden = view !== "ask";
  $("view-monitor").hidden = view !== "monitor";
  $("nav-ask").classList.toggle("on", view === "ask");
  $("nav-monitor").classList.toggle("on", view === "monitor");
  $("nav-attacks").classList.remove("on");
  document.body.classList.remove("nav-open");
}
$("nav-ask").onclick = () => show("ask");
$("nav-monitor").onclick = () => show("monitor");
$("nav-attacks").onclick = () => {
  show("monitor");
  $("panel-attacks").scrollIntoView({ behavior: "smooth", block: "start" });
};
$("promo-btn").onclick = () => show("monitor");
function setLab(name) {
  $("lab-name").textContent = name;
  $("lab-av").textContent = name.split(/\s+/).map(w => w[0] || "").join("").slice(0, 2).toUpperCase() || "AC";
}
async function loadSettings() {
  try { setLab((await api("/api/settings")).lab_name); } catch (e) {}
}
async function renameLab() {
  const name = prompt("Name of your lab", $("lab-name").textContent);
  if (!name || !name.trim()) return;
  try {
    const s = await api("/api/settings", {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ lab_name: name.trim() })
    });
    setLab(s.lab_name);
  } catch (e) { alert("Could not rename the lab: " + e.message); }
}
$("lab-edit").onclick = renameLab;
loadSettings();
function promoHidden() {
  try { return localStorage.getItem("xdr-promo-hidden") === "1"; } catch (e) { return false; }
}
$("promo").hidden = promoHidden();
$("promo-x").onclick = () => {
  $("promo").hidden = true;
  try { localStorage.setItem("xdr-promo-hidden", "1"); } catch (e) {}
};
$("collapse-btn").onclick = () => {
  if (matchMedia("(max-width: 820px)").matches) document.body.classList.toggle("nav-open");
  else document.body.classList.toggle("collapsed");
};

// ---- monitor ----
let lastEvent = 0;
const KIND_ICON = { attack: "alert", system: "server", info: "activity" };

function setPill(el, cls, text) {
  el.className = "pill " + cls + (el.classList.contains("hide-sm") ? " hide-sm" : "");
  el.querySelector("span:last-child").textContent = text;
}
function setHero(running) {
  $("orb").className = "orb" + (running ? "" : " paused");
  $("orb").replaceChildren(icon(running ? "radar" : "pause"));
  $("hero-title").textContent = running ? "Monitoring is live" : "Monitoring is paused";
  $("hero-sub").textContent = running
    ? "Every new Wazuh alert is checked automatically. Pause to stop checking."
    : "Chat still works. New alerts are queued and checked when you start again.";
  $("promo-title").textContent = running ? "Monitoring is live" : "Monitoring is paused";
  $("promo-sub").textContent = running
    ? "Every new Wazuh alert is checked automatically."
    : "Alerts are queued until you start monitoring again.";
}

function attackCard(a) {
  const sev = a.severity || "low";
  const card = h("article", "attack " + sev);
  const head = h("div", "attack-head");
  const title = h("div", "attack-title");
  title.append(icon(sev === "high" || sev === "critical" ? "alert" : "shield"), h("span", "", a.name || "Attack"));
  head.append(title, h("span", "sevtag", sev));
  const meta = h("div", "meta");
  meta.append(icon("clock", "sm"), h("span", "", [
    fmtTime(a.ts), a.rule_desc, `level ${a.level}`, `source ${a.srcip || "n/a"}`, `agent ${a.agent || "n/a"}`
  ].filter(Boolean).join("  ·  ")));
  card.append(head, meta, h("p", "", a.summary || ""));
  const steps = (a.details && a.details.steps) || [];
  if (steps.length) {
    card.append(h("div", "steps-title", "How to stop it"));
    const ol = h("ol");
    steps.forEach(s => ol.append(h("li", "", s)));
    card.append(ol);
  }
  const links = (a.details && a.details.links) || [];
  if (links.length) {
    const box = h("div", "links");
    links.forEach(([label, url]) => {
      const l = h("a", "", label);
      l.href = url;
      l.target = "_blank";
      l.rel = "noopener";
      l.prepend(icon("link", "sm"));
      box.append(l);
    });
    card.append(box);
  }
  return card;
}

function renderAttacks(items) {
  $("attack-count").textContent = items.length;
  $("nav-attack-count").textContent = items.length;
  const box = $("attacks");
  box.replaceChildren();
  if (!items.length) {
    box.append(h("p", "empty", "No attacks detected yet. Every new alert is checked automatically."));
    return;
  }
  items.forEach(a => box.append(attackCard(a)));
}

function addEvent(e) {
  lastEvent = Math.max(lastEvent, e.id);
  const box = $("events");
  const kind = KIND_ICON[e.kind] ? e.kind : "info";
  const row = h("div", "ev k-" + kind);
  const wrap = h("div", "ico-wrap");
  wrap.append(icon(KIND_ICON[kind]));
  const body = h("div");
  body.append(h("div", "meta", `${fmtTime(e.created)} · ${e.kind}`), h("div", "body", e.text));
  row.append(wrap, body);
  box.prepend(row);
  while (box.children.length > 100) box.lastChild.remove();
}

async function refreshMonitor() {
  try {
    const s = await api("/api/status");
    const running = s.monitor === "running";
    setPill($("pill-monitor"), running ? "ok" : "warn", running ? "Monitoring live" : "Paused");
    setPill($("pill-indexer"), s.indexer === "ok" ? "ok" : s.indexer === "error" ? "bad" : "warn",
            "Indexer " + s.indexer);
    setHero(running);
    $("stat-alerts").textContent = s.alerts;
    $("stat-attacks").textContent = s.attacks;
    $("stat-high").textContent = s.high;
    $("nav-alerts").textContent = s.alerts;
    $("stat-latest").textContent = fmtTime(s.last_alert) || "none";
    $("stat-poll").textContent = fmtTime(s.last_poll) || "never";
    $("stat-indexer").textContent = s.indexer;
    $("btn-start").disabled = running;
    $("btn-pause").disabled = !running;
    renderAttacks(await api("/api/attacks"));
    (await api(`/api/events?after=${lastEvent}`)).forEach(addEvent);
  } catch (e) {
    setPill($("pill-indexer"), "bad", "Dashboard offline");
  }
}

async function monitorAction(action) {
  try { await api(`/api/monitor/${action}`, { method: "POST" }); } catch (e) {}
  refreshMonitor();
}
$("btn-start").onclick = () => monitorAction("start");
$("btn-pause").onclick = () => monitorAction("pause");

// ---- chats ----
let currentChat = null, busy = false;

async function patchChat(id, body) {
  await api(`/api/chats/${id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
  });
  if (id === currentChat) await openChat(id);
  else await loadChats();
}

function chatRow(c) {
  const row = h("div", "chat" + (c.id === currentChat ? " on" : ""));
  row.onclick = () => openChat(c.id);
  if (c.pinned) row.append(icon("pin", "sm"));
  row.append(h("span", "t", c.title));
  const acts = h("div", "acts");
  acts.append(
    iconBtn("tiny" + (c.pinned ? " on" : ""), "pin", c.pinned ? "Unpin chat" : "Pin chat",
      ev => { ev.stopPropagation(); patchChat(c.id, { pinned: !c.pinned }); }),
    iconBtn("tiny", "pencil", "Rename chat", ev => {
      ev.stopPropagation();
      const name = prompt("New name for this chat", c.title);
      if (name && name.trim()) patchChat(c.id, { title: name.trim() });
    }),
    iconBtn("tiny danger", "trash", "Delete chat", ev => {
      ev.stopPropagation();
      removeChat(c.id);
    })
  );
  row.append(acts);
  return row;
}

function groupOf(c, today, yesterday) {
  if (c.pinned) return "Pinned";
  const k = dayKey(parseTs(c.created));
  if (k === today) return "Today";
  if (k === yesterday) return "Yesterday";
  return "Earlier";
}

async function loadChats() {
  const list = $("chatlist");
  let chats = [];
  try { chats = await api("/api/chats"); } catch (e) { return; }
  const q = $("search").value.trim().toLowerCase();
  if (q) chats = chats.filter(c => c.title.toLowerCase().includes(q));
  const today = dayKey(new Date());
  const yesterday = dayKey(new Date(Date.now() - 864e5));
  const groups = { Pinned: [], Today: [], Yesterday: [], Earlier: [] };
  chats.forEach(c => groups[groupOf(c, today, yesterday)].push(c));
  list.replaceChildren();
  if (!chats.length) {
    list.append(h("p", "empty-side", q ? "No chats match your search." : "No conversations yet."));
    return;
  }
  Object.entries(groups).forEach(([name, items]) => {
    if (!items.length) return;
    list.append(h("div", "grp", name));
    items.forEach(c => list.append(chatRow(c)));
  });
}
$("search").oninput = () => loadChats();

function showWelcome() {
  currentChat = null;
  $("messages").replaceChildren(welcomeEl());
  loadChats();
}

function welcomeEl() {
  const w = h("div", "welcome");
  const big = h("div", "big");
  big.append(icon("sparkle"));
  w.append(big,
    h("div", "kicker", "A space for your next security question"),
    h("h1", "", "Where should we begin?"),
    h("p", "lead", "Ask about your alerts, attacks, commands, Linux, Kubernetes, or XDR."));
  const cards = h("div", "cards");
  [
    { t: "Review attacks", d: "What attacks happened in the last hour, and how do I stop them?", i: "alert", tile: "t-alert",
      p: "What attacks happened in the last hour, and how do I stop them?" },
    { t: "Explain a command", d: "Show the commands to check the Wazuh indexer from a Linux VM.", i: "terminal", tile: "t-cmd",
      p: "Show the commands to check the Wazuh indexer from a Linux VM" },
    { t: "Make a report", d: "Make a PDF report about the attacks so far.", i: "file", tile: "t-file",
      p: "Make a PDF report about the attacks so far" }
  ].forEach(c => {
    const b = h("button", "card");
    b.append(h("span", "arrow"), h("div", "tile " + c.tile));
    b.querySelector(".arrow").append(icon("arrow", "sm"));
    b.querySelector(".tile").append(icon(c.i));
    b.append(h("h3", "", c.t), h("p", "", c.d));
    b.onclick = () => sendMessage(c.p);
    cards.append(b);
  });
  w.append(cards, h("p", "not-sure", "Not sure? Start with a question about your alerts."));
  return w;
}

function renderText(text) {
  const frag = document.createDocumentFragment();
  text.split("```").forEach((part, i) => {
    if (i % 2 === 1) {
      const lines = part.split("\n");
      let lang = "";
      if (lines.length > 1 && /^[\w+#.-]+$/.test(lines[0].trim())) lang = lines.shift().trim();
      frag.append(codeBlock(lines.join("\n").replace(/\n+$/, ""), lang));
    } else {
      part.trim().split(/\n\s*\n/).filter(p => p.trim()).forEach(p => {
        const para = h("p");
        appendInline(para, p.trim());
        frag.append(para);
      });
    }
  });
  return frag;
}

function appendInline(el, s) {
  s.split(/(`[^`\n]+`)/).forEach(seg => {
    if (seg.length > 2 && seg.startsWith("`") && seg.endsWith("`")) el.append(h("code", "", seg.slice(1, -1)));
    else if (seg) el.append(document.createTextNode(seg));
  });
}

function codeBlock(code, lang) {
  const box = h("div", "code");
  const bar = h("div", "codebar");
  const shell = ["bash", "sh", "shell", "zsh", "console"].includes(lang.toLowerCase());
  const label = h("span", "lbl" + (shell ? " cmd" : ""));
  label.append(icon(shell ? "terminal" : "code", "sm"), h("span", "", shell ? "Command" : (lang || "Code")));
  const copy = h("button");
  copy.append(icon("copy", "sm"), h("span", "", "Copy"));
  copy.onclick = async () => {
    try {
      await navigator.clipboard.writeText(code);
      copy.replaceChildren(icon("check", "sm"), h("span", "", "Copied"));
    } catch (e) {
      copy.replaceChildren(h("span", "", "Failed"));
    }
    setTimeout(() => copy.replaceChildren(icon("copy", "sm"), h("span", "", "Copy")), 1400);
  };
  bar.append(label, copy);
  box.append(bar, h("pre", "", code));
  return box;
}

function renderTurn(m) {
  if (m.role === "user") {
    const t = h("div", "turn user");
    t.append(h("div", "bubble", m.text));
    return t;
  }
  const t = h("div", "turn" + (m.error ? " error" : ""));
  const av = h("div", "av");
  av.append(icon("sparkle", "sm"));
  const body = h("div", "body");
  if (m.error) body.append(h("p", "", m.text));
  else body.append(renderText(m.text));
  if (m.file) {
    const a = h("a", "filelink");
    a.append(icon("download", "sm"), h("span", "", m.file.endsWith(".pdf") ? "Download PDF" : "Download PowerPoint"));
    a.href = m.file;
    a.target = "_blank";
    a.rel = "noopener";
    body.append(a);
  }
  t.append(av, body);
  return t;
}

async function openChat(id) {
  currentChat = id;
  const chat = await api(`/api/chats/${id}`);
  $("messages").replaceChildren();
  const box = $("messages");
  if (!chat.messages.length) box.append(welcomeEl());
  else {
    chat.messages.forEach(m => box.append(renderTurn(m)));
    box.scrollTop = box.scrollHeight;
  }
  loadChats();
}

async function newChat() {
  try {
    const c = await api("/api/chats", { method: "POST" });
    currentChat = c.id;
  } catch (e) {
    alert("Could not create a chat: " + e.message);
    return false;
  }
  $("messages").replaceChildren(welcomeEl());
  loadChats();
  $("q").focus();
  return true;
}

async function removeChat(id) {
  if (!confirm("Delete this chat permanently?")) return;
  await api(`/api/chats/${id}`, { method: "DELETE" });
  if (currentChat === id) showWelcome();
  else loadChats();
}

async function sendMessage(text) {
  text = (text || "").trim();
  if (!text || busy) return;
  if (!currentChat && !(await newChat())) return;
  busy = true;
  $("send").disabled = true;
  const box = $("messages");
  box.querySelector(".welcome")?.remove();
  box.append(renderTurn({ role: "user", text }));
  const typing = h("div", "turn");
  const av = h("div", "av");
  av.append(icon("sparkle", "sm"));
  const body = h("div", "body");
  const dots = h("div", "dots");
  dots.append(h("i"), h("i"), h("i"));
  body.append(dots);
  typing.append(av, body);
  box.append(typing);
  box.scrollTop = box.scrollHeight;
  const chatId = currentChat;
  try {
    await api(`/api/chats/${chatId}/messages`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: text })
    });
    await openChat(chatId);
  } catch (e) {
    typing.remove();
    box.append(renderTurn({ role: "assistant", text: e.message, error: true }));
    box.scrollTop = box.scrollHeight;
  } finally {
    busy = false;
    $("send").disabled = false;
  }
  $("q").focus();
}

// ---- composer ----
const q = $("q");
function autoSize() {
  q.style.height = "auto";
  q.style.height = Math.min(q.scrollHeight, 180) + "px";
}
q.addEventListener("input", autoSize);
q.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    const text = q.value;
    q.value = "";
    autoSize();
    sendMessage(text);
  }
});
$("send").onclick = () => {
  const text = q.value;
  q.value = "";
  autoSize();
  sendMessage(text);
};
document.querySelectorAll(".chipbtn").forEach(b => {
  b.onclick = () => {
    q.value = b.dataset.prompt;
    autoSize();
    q.focus();
  };
});
$("btn-new").onclick = () => { show("ask"); newChat(); };
document.addEventListener("keydown", e => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    show("ask");
    newChat();
  }
});

paintIcons();
paintTheme();
setPill($("pill-monitor"), "warn", "Connecting");
show("ask");
showWelcome();
refreshMonitor();
setInterval(refreshMonitor, 4000);
</script>
</body>
</html>"""
