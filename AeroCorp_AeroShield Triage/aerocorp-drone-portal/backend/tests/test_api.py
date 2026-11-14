"""End-to-end API tests against a real PostgreSQL database.

Run the suite twice, once per build:

    VULN_MODE=true  pytest -q      # weaknesses must be present
    VULN_MODE=false pytest -q      # the same weaknesses must be gone

The hardened run expects the admin password in ADMIN_PASSWORD (default for the vulnerable build is admin123).
"""
import os
import time

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.security import limiter

VULN = settings.vuln_mode
ADMIN_PW = os.getenv("ADMIN_PASSWORD") or "admin123"

only_vuln = pytest.mark.skipif(not VULN, reason="weakness exists only in the vulnerable build")
only_hardened = pytest.mark.skipif(VULN, reason="protection exists only in the hardened build")

XSS = '<img src=x onerror=alert(1)>'


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_limits():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture()
def admin_headers(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


# ----------------------------------------------------------------------------- shared behaviour
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert ("mode" in r.json()) == VULN


def test_categories_cover_whole_catalogue(client):
    cats = client.get("/api/categories").json()
    assert [c["name"] for c in cats][:2] == ["Consumer & creator", "FPV & racing"]
    assert sum(c["count"] for c in cats) == 18


def test_drone_list_pagination_and_sort(client):
    r = client.get("/api/drones?limit=5&page=2&sort=name").json()
    assert len(r["items"]) == 5 and r["page"] == 2 and r["pages"] == 4 and r["total"] == 18
    names = [d["name"] for d in r["items"]]
    assert names == sorted(names)


def test_drone_list_category_filter(client):
    r = client.get("/api/drones", params={"category": "Agriculture"}).json()
    assert r["total"] == 2 and all(d["category"] == "Agriculture" for d in r["items"])


def test_drone_detail_and_404(client):
    r = client.get("/api/drones/dji-mavic-3-pro")
    assert r.status_code == 200
    body = r.json()
    assert body["specs"]["flight_time_min"] == 43 and body["datasheet_url"].endswith("dji-mavic-3-pro.txt")
    assert all(x["category"] == body["category"] for x in body["related"])
    assert client.get("/api/drones/does-not-exist").status_code == 404


def test_posts(client):
    r = client.get("/api/posts").json()
    assert r["total"] == 6
    slug = r["items"][0]["slug"]
    detail = client.get(f"/api/posts/{slug}").json()
    assert "body" in detail and detail["body"]
    assert client.get("/api/posts/nope").status_code == 404


def test_search_finds_drones_and_posts(client):
    r = client.get("/api/search", params={"q": "mavic"}).json()
    assert any(d["name"] == "DJI Mavic 3 Pro" for d in r["drones"])
    r = client.get("/api/search", params={"q": "battery"}).json()
    assert r["posts"], "blog posts should be searchable"


def test_search_category_filter_and_blank(client):
    r = client.get("/api/search", params={"q": "DJI", "category": "Agriculture"}).json()
    assert r["drones"] and all(d["category"] == "Agriculture" for d in r["drones"])
    assert client.get("/api/search", params={"q": "   "}).json()["count"] == 0


def test_newsletter_signup(client):
    email = f"reader{time.time_ns()}@example.com"
    r = client.post("/api/newsletter", json={"email": email})
    assert r.status_code == 201 and r.json()["ok"] is True


def test_contact_valid_message(client):
    r = client.post("/api/contact", json={"name": "Sam", "email": "sam@example.com", "subject": "Hi", "message": "Do you ship to Cairo?"})
    assert r.status_code == 201 and r.json()["ok"] is True


def test_admin_requires_token(client):
    assert client.get("/api/admin/messages").status_code == 401


def test_admin_endpoints_with_token(client, admin_headers):
    assert client.get("/api/admin/stats", headers=admin_headers).json()["drones"] == 18
    assert isinstance(client.get("/api/admin/messages", headers=admin_headers).json(), list)
    assert isinstance(client.get("/api/admin/subscribers", headers=admin_headers).json(), list)
    assert isinstance(client.get("/api/admin/quotes", headers=admin_headers).json(), list)


def test_login_success_and_me(client, admin_headers):
    r = client.get("/api/auth/me", headers=admin_headers).json()
    assert r == {"username": "admin", "role": "admin"}


def test_non_admin_token_is_forbidden(client):
    if not VULN:
        pytest.skip("no sales account in the hardened seed")
    token = client.post("/api/auth/login", json={"username": "sales", "password": "Welcome1"}).json()["token"]
    assert client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_tampered_token_rejected(client, admin_headers):
    token = admin_headers["Authorization"].split()[1]
    bad = token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB")
    assert client.get("/api/admin/stats", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_datasheet_download_legit_file(client):
    r = client.get("/api/datasheets/download", params={"file": "dji-mavic-3-pro.txt"})
    assert r.status_code == 200 and "DJI Mavic 3 Pro" in r.text


def test_robots_lists_hidden_paths(client):
    assert "Disallow: /admin" in client.get("/robots.txt").text


def test_every_request_is_logged_as_json(client):
    marker = f"/api/drones?limit=1&marker={time.time_ns()}"
    client.get(marker, headers={"X-Real-IP": "203.0.113.9"})
    lines = (settings.log_dir / "app.log").read_text().splitlines()[-20:]
    import json

    records = [json.loads(line) for line in lines]
    hit = [r for r in records if r.get("event") == "http_request" and "marker=" in r.get("query", "") and marker.split("marker=")[1] in r["query"]]
    assert hit and hit[-1]["client_ip"] == "203.0.113.9" and hit[-1]["status"] == 200


# ----------------------------------------------------------------------------- vulnerable build
@only_vuln
def test_sqli_error_based_leaks_database_error(client):
    r = client.get("/api/search", params={"q": "'"})
    assert r.status_code == 500
    error = r.json()["error"].lower()
    assert "unterminated" in error or "syntax error" in error
    assert "SELECT" in r.json()["query"]  # the full SQL statement is echoed back


@only_vuln
def test_sqli_union_reads_other_tables(client):
    payload = "zzz%') UNION SELECT id, username, password_hash, role, 'x', 'x', 'x' FROM users --"
    r = client.get("/api/search", params={"q": payload}).json()
    # Column 2 of the original query is `slug`, column 3 is `name`.
    assert {"admin", "sales"} <= {d["slug"] for d in r["drones"]}
    assert any(str(d["name"]).startswith("pbkdf2_sha256$") for d in r["drones"])


@only_vuln
def test_sqli_boolean_changes_result_set(client):
    all_rows = client.get("/api/search", params={"q": "zzz%') OR 1=1 --"}).json()
    none = client.get("/api/search", params={"q": "zzz%') AND 1=2 --"}).json()
    assert len(all_rows["drones"]) == 18 and none["drones"] == []


@only_vuln
def test_sqli_time_based(client):
    started = time.perf_counter()
    r = client.get("/api/search", params={"q": "zzz%') AND (SELECT 1 FROM pg_sleep(2))=1 --"})
    assert r.status_code == 200 and time.perf_counter() - started >= 1.8


@only_vuln
def test_sqli_cannot_write_or_drop(client):
    r = client.get("/api/search", params={"q": "zzz%'); DELETE FROM users; --"})
    assert r.status_code == 500 and "permission denied" in r.json()["error"].lower()
    login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login.status_code == 200, "users table must survive injection attempts"


@only_vuln
def test_reflected_xss_payload_comes_back_raw(client):
    r = client.get("/api/search", params={"q": XSS}).json()
    assert r["query_display"] == XSS


@only_vuln
def test_stored_xss_reaches_admin_inbox_raw(client, admin_headers):
    client.post("/api/contact", json={"name": XSS, "email": "x@example.com", "subject": "s", "message": f"hello {XSS}"})
    first = client.get("/api/admin/messages", headers=admin_headers).json()[0]
    assert XSS in first["message_html"] and XSS in first["name_html"]


@only_vuln
def test_contact_accepts_huge_and_invalid_input(client):
    r = client.post("/api/contact", json={"name": "a" * 5000, "email": "not-an-email", "message": "b" * 100_000})
    assert r.status_code == 201 and "id" in r.json()


@only_vuln
def test_no_rate_limit_on_forms(client):
    codes = [client.post("/api/contact", json={"name": "bot", "email": "b@example.com", "message": "spam spam"}).status_code for _ in range(30)]
    assert set(codes) == {201}


@only_vuln
def test_newsletter_reveals_existing_subscribers(client):
    email = f"dupe{time.time_ns()}@example.com"
    assert client.post("/api/newsletter", json={"email": email}).status_code == 201
    r = client.post("/api/newsletter", json={"email": email})
    assert r.status_code == 409 and "already subscribed" in r.json()["detail"]


@only_vuln
def test_idor_quote_readable_without_token(client):
    created = client.post("/api/quotes", json={"drone_slug": "dji-agras-t40", "contact_name": "Victim", "email": "victim@example.com", "quantity": 3, "notes": "private"}).json()
    r = client.get(f"/api/quotes/{created['id']}")
    assert r.status_code == 200 and r.json()["email"] == "victim@example.com"


@only_vuln
def test_path_traversal_reads_system_file(client):
    r = client.get("/api/datasheets/download", params={"file": "../" * 8 + "etc/passwd"})
    assert r.status_code == 200 and "root:" in r.text


@only_vuln
def test_missing_file_leaks_server_path(client):
    r = client.get("/api/datasheets/download", params={"file": "nope.txt"})
    assert r.status_code == 404 and "datasheets" in r.json()["detail"]


@only_vuln
def test_login_distinguishes_unknown_user_from_wrong_password(client):
    unknown = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    wrong = client.post("/api/auth/login", json={"username": "admin", "password": "x"})
    assert unknown.json()["detail"] == "Unknown user" and wrong.json()["detail"] == "Incorrect password"


@only_vuln
def test_login_has_no_lockout_so_brute_force_succeeds(client):
    for i in range(15):
        assert client.post("/api/auth/login", json={"username": "admin", "password": f"guess{i}"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200


@only_vuln
def test_honeytokens_and_docs_are_exposed(client):
    assert "FAKE-SECRET-KEY" in client.get("/.env").text
    assert "FAKE-HASH" in client.get("/backup/site-backup.sql").text
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200


@only_vuln
def test_wildcard_cors(client):
    r = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") == "*"


@only_vuln
def test_unhandled_errors_are_verbose(client):
    r = client.get("/api/datasheets/download", params={"file": "../" * 8 + "etc"})  # a directory
    assert r.status_code == 500 and "trace" in r.json()


# ----------------------------------------------------------------------------- hardened build
@only_hardened
def test_sqli_payloads_are_just_text(client):
    for payload in ("'", "zzz%') OR 1=1 --", "x') UNION SELECT 1,2,3,4,5,6,7 FROM users --"):
        r = client.get("/api/search", params={"q": payload})
        assert r.status_code == 200, payload
        assert r.json()["drones"] == [], "payload must be matched as plain text, never executed"
    long_union = "zzz%') UNION SELECT id, username, password_hash, role, 'x', 'x', 'x' FROM users --"
    assert client.get("/api/search", params={"q": long_union}).status_code == 422  # over the 80-character limit


@only_hardened
def test_search_length_limit_and_rate_limit(client):
    assert client.get("/api/search", params={"q": "a" * 81}).status_code == 422
    codes = [client.get("/api/search", params={"q": "dji"}).status_code for _ in range(32)]
    assert codes.count(429) >= 1 and codes[0] == 200


@only_hardened
def test_percent_and_underscore_are_literal_in_search(client):
    assert client.get("/api/search", params={"q": "%"}).json()["drones"] == []
    assert client.get("/api/search", params={"q": "_"}).json()["drones"] == []


@only_hardened
def test_reflected_output_is_escaped(client):
    r = client.get("/api/search", params={"q": XSS}).json()
    assert "<" not in r["query_display"] and "&lt;img" in r["query_display"]


@only_hardened
def test_stored_output_is_escaped(client, admin_headers):
    client.post("/api/contact", json={"name": "Eve", "email": "eve@example.com", "subject": "s", "message": f"hello {XSS}"})
    first = client.get("/api/admin/messages", headers=admin_headers).json()[0]
    assert "<img" not in first["message_html"] and "&lt;img" in first["message_html"]


@only_hardened
def test_contact_validation_honeypot_and_rate_limit(client):
    assert client.post("/api/contact", json={"name": "a" * 500, "email": "x@example.com", "message": "hello there"}).status_code == 422
    assert client.post("/api/contact", json={"name": "Bob", "email": "nope", "message": "hello there"}).status_code == 422
    assert client.post("/api/contact", json={"name": "Bob", "email": "bob@example.com", "message": "x" * 2001}).status_code == 422
    bot = client.post("/api/contact", json={"name": "Bot", "email": "bot@example.com", "message": "buy now", "website": "http://spam"})
    assert bot.status_code == 201 and bot.json() == {"ok": True}
    limiter.reset()
    codes = [client.post("/api/contact", json={"name": "Ann", "email": "ann@example.com", "message": "hello again"}).status_code for _ in range(7)]
    assert codes[:5] == [201] * 5 and codes[5:] == [429, 429]


@only_hardened
def test_newsletter_is_uniform_and_validated(client):
    email = f"uniform{time.time_ns()}@example.com"
    first = client.post("/api/newsletter", json={"email": email})
    second = client.post("/api/newsletter", json={"email": email})
    assert first.status_code == second.status_code == 201 and first.json() == second.json()
    assert client.post("/api/newsletter", json={"email": "bad"}).status_code == 422
    limiter.reset()
    codes = [client.post("/api/newsletter", json={"email": f"r{i}{time.time_ns()}@example.com"}).status_code for i in range(7)]
    assert 429 in codes


@only_hardened
def test_idor_needs_token_or_admin(client, admin_headers):
    created = client.post("/api/quotes", json={"drone_slug": "dji-agras-t40", "contact_name": "Owner", "email": "owner@example.com", "quantity": 3}).json()
    qid = created["id"]
    assert client.get(f"/api/quotes/{qid}").status_code == 404
    assert client.get(f"/api/quotes/{qid}", params={"token": "wrong"}).status_code == 404
    assert client.get(f"/api/quotes/{qid}", params={"token": created["token"]}).status_code == 200
    assert client.get(f"/api/quotes/{qid}", headers=admin_headers).status_code == 200


@only_hardened
def test_path_traversal_blocked(client):
    for bad in ("../" * 8 + "etc/passwd", "..%2f..%2fetc%2fpasswd", "/etc/passwd", "dji-mavic-3-pro.txt/../../x.txt", "nope.txt", "x.txt\x00.png"):
        assert client.get("/api/datasheets/download", params={"file": bad}).status_code == 404


@only_hardened
def test_login_generic_error_and_lockout(client):
    unknown = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    wrong = client.post("/api/auth/login", json={"username": "admin", "password": "x"})
    assert unknown.json() == wrong.json() and unknown.status_code == wrong.status_code == 401
    limiter.reset()
    for i in range(5):
        assert client.post("/api/auth/login", json={"username": "locktest", "password": f"g{i}"}).status_code == 401
    locked = client.post("/api/auth/login", json={"username": "locktest", "password": "g6"})
    assert locked.status_code == 429 and "Retry-After" in locked.headers


@only_hardened
def test_login_ip_rate_limit(client):
    codes = [client.post("/api/auth/login", json={"username": f"u{i}", "password": "x"}).status_code for i in range(12)]
    assert codes[:10] == [401] * 10 and codes[10:] == [429, 429]


@only_hardened
def test_honeytokens_docs_and_cors_closed(client):
    assert client.get("/.env").status_code == 404
    assert client.get("/backup/site-backup.sql").status_code == 404
    assert client.get("/api/docs").status_code == 404 and client.get("/api/openapi.json").status_code == 404
    r = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


@only_hardened
def test_security_headers_and_global_rate_limit(client):
    r = client.get("/api/drones")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in r.headers["content-security-policy"]
    codes = [client.get("/api/categories").status_code for _ in range(250)]
    assert 429 in codes


@only_hardened
def test_errors_are_not_verbose(client):
    r = client.get("/api/quotes/not-a-number")
    assert r.status_code == 422
    assert "trace" not in r.text
