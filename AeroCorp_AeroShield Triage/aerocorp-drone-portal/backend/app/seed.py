import argparse
import json
import secrets
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .db import Base, SessionLocal, engine, ensure_schema, wait_for_db
from .models import ContactMessage, Drone, Post, QuoteRequest, Subscriber, User  # noqa: F401
from .security import hash_password
from .seed_data import DEMO_USERS, DRONES, POSTS
from .util import slugify

SPEC_LABELS = {
    "flight_time_min": ("Flight time", "min"),
    "endurance_h": ("Endurance", "h"),
    "max_range_km": ("Max range", "km"),
    "max_speed_kmh": ("Max speed", "km/h"),
    "ceiling_m": ("Service ceiling", "m"),
    "weight_kg": ("Weight", "kg"),
    "payload_kg": ("Payload", "kg"),
    "wingspan_m": ("Wingspan", "m"),
    "camera": ("Camera", ""),
    "ip_rating": ("Ingress protection", ""),
    "notes": ("Notes", ""),
}


def write_datasheet(drone: Drone) -> Path:
    settings.datasheet_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"AEROCORP DATASHEET - {drone.name}",
        "=" * 60,
        f"Manufacturer : {drone.manufacturer}",
        f"Category     : {drone.category}",
        "",
        drone.description or "",
        "",
        "Specifications",
        "-" * 14,
    ]
    for key, value in (drone.specs or {}).items():
        label, unit = SPEC_LABELS.get(key, (key.replace("_", " ").title(), ""))
        lines.append(f"{label:<20}: {value} {unit}".rstrip())
    if drone.price_usd:
        lines.append(f"{'List price':<20}: USD {drone.price_usd:,}")
    else:
        lines.append(f"{'List price':<20}: on request")
    if drone.source_url:
        lines += ["", f"Source: {drone.source_url}"]
    lines += ["", "Figures are approximate. Confirm with the manufacturer before purchase.", ""]
    path = settings.datasheet_dir / f"{drone.slug}.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def seed_if_empty(db: Session) -> dict:
    added = {"drones": 0, "posts": 0, "users": 0}

    if db.scalar(select(func.count()).select_from(Drone)) == 0:
        for item in DRONES:
            db.add(Drone(slug=slugify(item["name"]), **item))
            added["drones"] += 1
        db.commit()

    if db.scalar(select(func.count()).select_from(Post)) == 0:
        for item in POSTS:
            db.add(Post(slug=slugify(item["title"]), **item))
            added["posts"] += 1
        db.commit()

    if db.scalar(select(func.count()).select_from(User)) == 0:
        if settings.vuln_mode:
            for account in DEMO_USERS:
                db.add(User(username=account["username"], password_hash=hash_password(account["password"]), role=account["role"]))
                added["users"] += 1
        else:
            password = settings.admin_password or secrets.token_urlsafe(12)
            db.add(User(username="admin", password_hash=hash_password(password), role="admin"))
            added["users"] += 1
            if not settings.admin_password:
                print(f"[seed] Generated admin password (shown once): {password}", flush=True)
        db.commit()

    for drone in db.scalars(select(Drone)):
        if not (settings.datasheet_dir / f"{drone.slug}.txt").exists():
            write_datasheet(drone)
    return added


def upsert_scraped(db: Session, items: list[dict], new_status: str = "pending") -> dict:
    """Merge scraper output into the catalogue. Only non-empty fields overwrite existing values.

    New drones are created with `new_status`. The default "pending" keeps them off the website until an
    admin approves them in the Products tab. Existing drones keep their status.
    """
    counts = {"updated": 0, "created": 0, "skipped": 0}
    for item in items:
        slug = item.get("slug") or (slugify(item["name"]) if item.get("name") else None)
        if not slug:
            counts["skipped"] += 1
            continue
        drone = db.scalar(select(Drone).where(Drone.slug == slug))
        if drone is None:
            if not (item.get("name") and item.get("category")):
                counts["skipped"] += 1
                continue
            drone = Drone(slug=slug, name=item["name"], manufacturer=item.get("manufacturer", "Unknown"),
                          category=item["category"], description="", specs={}, status=new_status)
            db.add(drone)
            counts["created"] += 1
        elif drone.manual_edit:  # an admin edited this aircraft by hand: leave it alone
            counts["kept_manual"] = counts.get("kept_manual", 0) + 1
            continue
        else:
            counts["updated"] += 1
        for field in ("description", "image_url", "image_credit", "source_url", "price_usd"):
            if item.get(field):
                setattr(drone, field, item[field])
        if item.get("specs"):
            drone.specs = {**(drone.specs or {}), **item["specs"]}
        db.flush()
        write_datasheet(drone)
    db.commit()
    return counts


def init_db() -> None:
    wait_for_db()
    Base.metadata.create_all(engine)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or reset the AeroCorp portal database")
    parser.add_argument("--reset", action="store_true", help="drop all tables first")
    parser.add_argument("--scraped", type=Path, help="merge a scraper JSON file into the catalogue")
    parser.add_argument("--publish-new", action="store_true",
                        help="publish new scraped drones straight away (default: they wait for admin approval)")
    args = parser.parse_args()

    wait_for_db()
    if args.reset:
        Base.metadata.drop_all(engine)
        print("[seed] dropped all tables")
    Base.metadata.create_all(engine)
    ensure_schema()
    with SessionLocal() as db:
        print("[seed] starter data added:", seed_if_empty(db))
        if args.scraped:
            items = json.loads(args.scraped.read_text(encoding="utf-8"))
            status = "published" if args.publish_new else "pending"
            print(f"[seed] scraped data merged (new drones: {status}):", upsert_scraped(db, items, new_status=status))


if __name__ == "__main__":
    main()
