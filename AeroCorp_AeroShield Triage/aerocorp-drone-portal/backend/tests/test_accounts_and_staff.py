"""Customer accounts, aircraft management, photo uploads and newsletters, against a real PostgreSQL database.

Run after the same reset as test_api.py, once per build:

    VULN_MODE=true  pytest -q tests/test_accounts_and_staff.py
    VULN_MODE=false ADMIN_PASSWORD=admin123 pytest -q tests/test_accounts_and_staff.py
"""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.security import limiter
from app.seed import upsert_scraped

VULN = settings.vuln_mode
ADMIN_PW = os.getenv("ADMIN_PASSWORD") or "admin123"
PASSWORD = "correct-horse-1"
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
JPEG = b"\xff\xd8\xff" + b"0" * 64

only_vuln = pytest.mark.skipif(not VULN, reason="only in the vulnerable build")
only_hardened = pytest.mark.skipif(VULN, reason="only in the hardened build")


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_limits_and_clean_up():
    limiter.reset()
    yield
    limiter.reset()
    _remove_test_products()


def _remove_test_products():
    """Other test modules count the catalogue, so every aircraft this module creates is deleted again."""
    from sqlalchemy import delete

    from app.models import Drone

    from app.models import Post

    with SessionLocal() as db:
        db.execute(delete(Drone).where(Drone.slug.like("test-rotor-%")))
        db.execute(delete(Post).where(Post.title.like("Test %")))
        db.commit()
    for folder, pattern in ((settings.media_dir / "drones", "test-rotor-*"), (settings.datasheet_dir, "test-rotor-*.txt")):
        for path in folder.glob(pattern):
            path.unlink()


@pytest.fixture()
def admin(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": ADMIN_PW})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def _customer(client):
    email = f"buyer-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/customers/register", json={"name": "Test Buyer", "email": email,
                                                     "password": PASSWORD, "company": "Acme Survey"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, email


def _new_product(client, admin, status="pending"):
    name = f"Test Rotor {uuid.uuid4().hex[:6]}"
    r = client.post("/api/admin/products", headers=admin, json={
        "name": name, "manufacturer": "Test Maker", "category": "Agriculture", "status": status,
        "price_usd": 1000, "specs": {"flight_time_min": 20}})
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------------- customer accounts
def test_customer_registers_signs_in_and_sees_profile(client):
    headers, email = _customer(client)
    me = client.get("/api/customers/me", headers=headers)
    assert me.status_code == 200 and me.json()["email"] == email and me.json()["company"] == "Acme Survey"
    login = client.post("/api/customers/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200 and login.json()["role"] == "customer"


def test_duplicate_registration_is_refused(client):
    _, email = _customer(client)
    r = client.post("/api/customers/register", json={"name": "Again", "email": email, "password": "another-pass-1"})
    if VULN:
        assert r.status_code == 409 and "already exists" in r.json()["detail"]
    else:
        assert r.status_code == 400 and "could not create" in r.json()["detail"]


@only_hardened
def test_hardened_login_errors_are_generic_and_lock_out(client):
    _, email = _customer(client)
    for _ in range(5):
        r = client.post("/api/customers/login", json={"email": email, "password": "wrong-password"})
        assert r.status_code == 401 and r.json()["detail"] == "Invalid email or password."
    assert client.post("/api/customers/login", json={"email": email, "password": PASSWORD}).status_code == 429


@only_vuln
def test_vulnerable_login_reveals_unknown_emails(client):
    r = client.post("/api/customers/login", json={"email": "nobody@example.com", "password": "x"})
    assert r.status_code == 401 and r.json()["detail"] == "No account with that email"


def test_customer_and_staff_tokens_do_not_cross(client, admin):
    customer, _ = _customer(client)
    assert client.get("/api/customers/me", headers=admin).status_code == 403
    assert client.get("/api/admin/products", headers=customer).status_code == 403
    assert client.get("/api/admin/campaigns", headers=customer).status_code == 403


def test_customer_saves_and_removes_favourites(client):
    headers, _ = _customer(client)
    assert client.post("/api/customers/me/favorites/dji-mavic-3-pro", headers=headers).status_code == 201
    assert [f["slug"] for f in client.get("/api/customers/me/favorites", headers=headers).json()] == ["dji-mavic-3-pro"]
    assert client.delete("/api/customers/me/favorites/dji-mavic-3-pro", headers=headers).status_code == 204
    assert client.get("/api/customers/me/favorites", headers=headers).json() == []


def test_quote_from_a_signed_in_customer_appears_in_their_account(client):
    headers, email = _customer(client)
    quote = client.post("/api/quotes", headers=headers, json={
        "drone_slug": "dji-mavic-3-pro", "contact_name": "Test Buyer", "email": email, "quantity": 2, "notes": "Survey"})
    assert quote.status_code == 201, quote.text
    mine = client.get("/api/customers/me/quotes", headers=headers).json()
    assert quote.json()["id"] in [row["id"] for row in mine]


# --------------------------------------------------------------------------- aircraft management
def test_new_aircraft_stays_off_the_site_until_published(client, admin):
    product = _new_product(client, admin, status="pending")
    assert client.get(f"/api/drones/{product['slug']}").status_code == 404
    r = client.post(f"/api/admin/products/{product['slug']}/status", headers=admin, json={"status": "published"})
    assert r.status_code == 200 and r.json()["status"] == "published"
    assert client.get(f"/api/drones/{product['slug']}").status_code == 200


def test_admin_edits_price_and_details_and_the_scraper_cannot_overwrite_them(client, admin):
    product = _new_product(client, admin, status="published")
    r = client.put(f"/api/admin/products/{product['slug']}", headers=admin,
                   json={"price_usd": 1500, "description": "Edited by the admin"})
    assert r.status_code == 200 and r.json()["manual_edit"] is True
    detail = client.get(f"/api/drones/{product['slug']}").json()
    assert detail["price_usd"] == 1500 and detail["description"] == "Edited by the admin"

    with SessionLocal() as db:
        counts = upsert_scraped(db, [{"slug": product["slug"], "name": product["name"], "category": "Agriculture",
                                      "manufacturer": "Test Maker", "price_usd": 999, "description": "scraped"}])
    assert counts.get("kept_manual") == 1
    assert client.get(f"/api/drones/{product['slug']}").json()["price_usd"] == 1500


def test_product_fields_are_validated(client, admin):
    product = _new_product(client, admin)
    url = f"/api/admin/products/{product['slug']}"
    assert client.put(url, headers=admin, json={"category": "Toys"}).status_code == 422
    assert client.put(url, headers=admin, json={"price_usd": -5}).status_code == 422
    assert client.put(url, headers=admin, json={"source_url": "javascript:alert(1)"}).status_code == 422
    assert client.put(url, headers=admin, json={"description": None}).status_code == 422


def test_staff_only_roles_cannot_manage_products(client, admin):
    customer, _ = _customer(client)
    assert client.post("/api/admin/products", headers=customer, json={
        "name": "Nope", "manufacturer": "X", "category": "Agriculture"}).status_code == 403


def test_photo_upload_replaces_the_image_with_a_cache_busting_url(client, admin):
    product = _new_product(client, admin)
    r = client.post(f"/api/admin/products/{product['slug']}/image", headers={**admin, "Content-Type": "image/png"}, content=PNG)
    assert r.status_code == 200, r.text
    url = r.json()["image_url"]
    assert url.startswith(f"/api/media/drones/{product['slug']}.png?v=")
    assert client.get(url.split("?")[0]).status_code == 200


@only_hardened
def test_hardened_photo_upload_checks_the_file_content(client, admin):
    product = _new_product(client, admin)
    url = f"/api/admin/products/{product['slug']}/image"
    assert client.post(url, headers={**admin, "Content-Type": "image/png"}, content=b"<svg onload=alert(1)>").status_code == 415
    assert client.post(url, headers={**admin, "Content-Type": "image/svg+xml"}, content=b"<svg/>").status_code == 415
    assert client.post(url, headers={**admin, "Content-Type": "image/jpeg"}, content=JPEG).status_code == 200


@only_vuln
def test_vulnerable_photo_upload_accepts_svg_without_checking_content(client, admin):
    product = _new_product(client, admin)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>'
    r = client.post(f"/api/admin/products/{product['slug']}/image", headers={**admin, "Content-Type": "image/svg+xml"}, content=svg)
    assert r.status_code == 200 and r.json()["image_url"].split("?")[0].endswith(".svg")


# --------------------------------------------------------------------------- newsletters
def test_admin_writes_edits_and_sends_a_newsletter(client, admin):
    r = client.post("/api/admin/campaigns", headers=admin, json={"subject": "Spring update", "body": "New aircraft."})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    cid = r.json()["id"]
    r = client.put(f"/api/admin/campaigns/{cid}", headers=admin, json={"subject": "Spring update 2", "body": "Edited."})
    assert r.status_code == 200 and r.json()["subject"] == "Spring update 2"
    sent = client.post(f"/api/admin/campaigns/{cid}/send", headers=admin)
    assert sent.status_code == 200 and sent.json()["status"] == "sent" and sent.json()["sent_at"]
    assert client.post(f"/api/admin/campaigns/{cid}/send", headers=admin).status_code == 409
    assert client.put(f"/api/admin/campaigns/{cid}", headers=admin, json={"subject": "x", "body": "y"}).status_code == 409


def test_customers_cannot_write_newsletters(client):
    customer, _ = _customer(client)
    assert client.post("/api/admin/campaigns", headers=customer, json={"subject": "x", "body": "y"}).status_code == 403


@only_vuln
def test_sales_staff_can_draft_but_not_send(client):
    r = client.post("/api/auth/login", json={"username": "sales", "password": "Welcome1"})
    sales = {"Authorization": f"Bearer {r.json()['token']}"}
    draft = client.post("/api/admin/campaigns", headers=sales, json={"subject": "From sales", "body": "Draft text."})
    assert draft.status_code == 201
    assert client.post(f"/api/admin/campaigns/{draft.json()['id']}/send", headers=sales).status_code == 403
    assert client.get("/api/admin/products", headers=sales).status_code == 403


# --------------------------------------------------------------------------- news articles
def _article(client, headers, title=None):
    title = title or f"Test article {uuid.uuid4().hex[:8]}"
    r = client.post("/api/admin/articles", headers=headers, json={
        "title": title, "summary": "Short summary.", "category": "Guides", "body": "First paragraph.\n\nSecond paragraph."})
    assert r.status_code == 201, r.text
    return r.json()


def test_draft_article_is_hidden_until_an_admin_publishes_it(client, admin):
    art = _article(client, admin)
    assert client.get(f"/api/posts/{art['slug']}").status_code == 404
    listed = client.get("/api/posts", params={"limit": 30}).json()["items"]
    assert art["slug"] not in [p["slug"] for p in listed]

    r = client.post(f"/api/admin/articles/{art['id']}/status", headers=admin, json={"status": "published"})
    assert r.status_code == 200 and r.json()["status"] == "published"
    live = client.get(f"/api/posts/{art['slug']}")
    assert live.status_code == 200 and live.json()["body"].startswith("First paragraph.")

    client.post(f"/api/admin/articles/{art['id']}/status", headers=admin, json={"status": "draft"})
    assert client.get(f"/api/posts/{art['slug']}").status_code == 404


def test_draft_articles_do_not_appear_in_search(client, admin):
    title = f"Test searchable {uuid.uuid4().hex[:8]}"
    _article(client, admin, title=title)
    found = client.get("/api/search", params={"q": title}).json()
    assert title not in [p["title"] for p in found.get("posts", [])]


def test_article_slug_stays_the_same_after_editing(client, admin):
    art = _article(client, admin)
    r = client.put(f"/api/admin/articles/{art['id']}", headers=admin, json={
        "title": "Completely new title", "summary": "New.", "category": "Safety", "body": "Edited."})
    assert r.status_code == 200 and r.json()["slug"] == art["slug"] and r.json()["category"] == "Safety"


def test_article_category_and_delete(client, admin):
    art = _article(client, admin)
    bad = client.put(f"/api/admin/articles/{art['id']}", headers=admin, json={
        "title": "x", "category": "Gossip", "body": "y"})
    assert bad.status_code == 422
    assert client.delete(f"/api/admin/articles/{art['id']}", headers=admin).status_code == 204
    assert client.get(f"/api/admin/articles", headers=admin).status_code == 200


def test_customers_cannot_write_articles(client):
    customer, _ = _customer(client)
    assert client.post("/api/admin/articles", headers=customer, json={
        "title": "Test nope", "category": "News", "body": "x"}).status_code == 403


@only_vuln
def test_sales_drafts_but_admin_publishes_and_deletes(client, admin):
    r = client.post("/api/auth/login", json={"username": "sales", "password": "Welcome1"})
    sales = {"Authorization": f"Bearer {r.json()['token']}"}
    art = _article(client, sales)
    assert art["status"] == "draft" and art["author"] == "sales"
    assert client.put(f"/api/admin/articles/{art['id']}", headers=sales, json={
        "title": "Test sales edit", "category": "News", "body": "Still a draft."}).status_code == 200
    assert client.post(f"/api/admin/articles/{art['id']}/status", headers=sales, json={"status": "published"}).status_code == 403
    assert client.delete(f"/api/admin/articles/{art['id']}", headers=sales).status_code == 403

    client.post(f"/api/admin/articles/{art['id']}/status", headers=admin, json={"status": "published"})
    assert client.put(f"/api/admin/articles/{art['id']}", headers=sales, json={
        "title": "Test sales late edit", "category": "News", "body": "Too late."}).status_code == 403
