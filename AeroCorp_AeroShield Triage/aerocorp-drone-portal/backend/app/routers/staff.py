import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..logging_setup import log_event
from ..models import Campaign, Drone, Post, Subscriber
from ..security import client_ip, require_admin, require_staff
from ..seed import write_datasheet
from ..seed_data import CATEGORIES
from ..util import clean_text, slugify

router = APIRouter()

IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
VULN_IMAGE_TYPES = {**IMAGE_TYPES, "image/svg+xml": ".svg"}
MAX_IMAGE_BYTES = 2_000_000
STATUSES = ("published", "pending")
ARTICLE_CATEGORIES = ["News", "Guides", "Safety", "Regulation", "Agriculture"]


class DroneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    manufacturer: str = Field(min_length=1, max_length=120)
    category: str
    status: str = "pending"
    description: str = Field(default="", max_length=5000)
    price_usd: int | None = None
    specs: dict = {}
    image_credit: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None, max_length=500)


class DroneUpdate(BaseModel):
    """Only the fields present in the request are changed."""

    name: str | None = Field(default=None, max_length=160)
    manufacturer: str | None = Field(default=None, max_length=120)
    category: str | None = None
    description: str | None = Field(default=None, max_length=5000)
    price_usd: int | None = None
    specs: dict | None = None
    image_credit: str | None = Field(default=None, max_length=300)
    source_url: str | None = Field(default=None, max_length=500)


class StatusIn(BaseModel):
    status: str


class CampaignIn(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=50_000)


# --------------------------------------------------------------------------- helpers
def _check(fields: dict) -> dict:
    """Validate the fields that are present. Returns them with text cleaned."""
    problems = []
    for key in ("name", "manufacturer", "category", "description", "specs"):
        if key in fields and fields[key] is None:
            problems.append(f"{key.capitalize()} cannot be empty.")
    if "name" in fields and not (fields["name"] or "").strip():
        problems.append("Name is required.")
    if "manufacturer" in fields and not (fields["manufacturer"] or "").strip():
        problems.append("Manufacturer is required.")
    if "category" in fields and fields["category"] not in CATEGORIES:
        problems.append(f"Category must be one of: {', '.join(CATEGORIES)}.")
    price = fields.get("price_usd")
    if price is not None and not 0 <= price <= 10_000_000:
        problems.append("Price must be between 0 and 10,000,000 USD (or empty for on request).")
    specs = fields.get("specs")
    if specs is not None and (len(specs) > 40 or not all(isinstance(v, (str, int, float)) for v in specs.values())):
        problems.append("Specs must be up to 40 entries, each a number or short text.")
    url = fields.get("source_url")
    if url and not url.startswith(("http://", "https://")):
        problems.append("The source link must start with http:// or https://.")
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))
    return {k: (clean_text(v) if isinstance(v, str) else v) for k, v in fields.items()}


def _product_out(d: Drone) -> dict:
    return {
        "id": d.id,
        "slug": d.slug,
        "name": d.name,
        "manufacturer": d.manufacturer,
        "category": d.category,
        "status": d.status,
        "manual_edit": d.manual_edit,
        "description": d.description or "",
        "price_usd": d.price_usd,
        "specs": d.specs or {},
        "image_url": d.image_url,
        "image_credit": d.image_credit,
        "source_url": d.source_url,
        "wiki_title": d.wiki_title,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }


def _drone_or_404(db: Session, slug: str) -> Drone:
    drone = db.scalar(select(Drone).where(Drone.slug == slug))
    if drone is None:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    return drone


def _campaign_out(c: Campaign) -> dict:
    return {
        "id": c.id,
        "subject": c.subject,
        "body": c.body,
        "status": c.status,
        "author": c.author,
        "recipients": c.recipients,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "sent_at": c.sent_at.isoformat() if c.sent_at else None,
    }


def _image_matches(data: bytes, ext: str) -> bool:
    if ext == ".jpg":
        return data[:3] == b"\xff\xd8\xff"
    if ext == ".png":
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


# --------------------------------------------------------------------------- aircraft (admin)
@router.get("/api/admin/products", dependencies=[Depends(require_admin)])
def list_products(status: str = "all", db: Session = Depends(get_db)):
    stmt = select(Drone).order_by(Drone.status.desc(), Drone.name)
    if status in STATUSES:
        stmt = stmt.where(Drone.status == status)
    return [_product_out(d) for d in db.scalars(stmt).all()]


@router.post("/api/admin/products", status_code=201, dependencies=[Depends(require_admin)])
def create_product(payload: DroneCreate, request: Request, db: Session = Depends(get_db)):
    if payload.status not in STATUSES:
        raise HTTPException(status_code=422, detail="Status must be published or pending.")
    fields = _check(payload.model_dump())
    slug = slugify(fields["name"])
    if db.scalar(select(Drone).where(Drone.slug == slug)) is not None:
        raise HTTPException(status_code=409, detail="An aircraft with that name already exists.")
    drone = Drone(slug=slug, description=fields.pop("description", ""), specs=fields.pop("specs", {}),
                  manual_edit=True, **{k: v for k, v in fields.items() if k != "status"},
                  status=payload.status)
    db.add(drone)
    db.commit()
    db.refresh(drone)
    write_datasheet(drone)
    log_event("product_created", client_ip=client_ip(request), slug=slug, status=drone.status)
    return _product_out(drone)


@router.get("/api/admin/products/{slug}", dependencies=[Depends(require_admin)])
def get_product(slug: str, db: Session = Depends(get_db)):
    return _product_out(_drone_or_404(db, slug))


@router.put("/api/admin/products/{slug}", dependencies=[Depends(require_admin)])
def update_product(slug: str, payload: DroneUpdate, request: Request, claims: dict = Depends(require_admin),
                   db: Session = Depends(get_db)):
    drone = _drone_or_404(db, slug)
    changes = _check(payload.model_dump(exclude_unset=True))
    if not changes:
        return _product_out(drone)
    for field, value in changes.items():
        setattr(drone, field, value)
    drone.manual_edit = True  # protects the aircraft from later scraper runs
    db.commit()
    write_datasheet(drone)
    log_event("product_updated", client_ip=client_ip(request), by=claims["sub"], slug=slug, fields=sorted(changes))
    return _product_out(drone)


@router.post("/api/admin/products/{slug}/status", dependencies=[Depends(require_admin)])
def set_status(slug: str, payload: StatusIn, request: Request, claims: dict = Depends(require_admin),
               db: Session = Depends(get_db)):
    if payload.status not in STATUSES:
        raise HTTPException(status_code=422, detail="Status must be published or pending.")
    drone = _drone_or_404(db, slug)
    drone.status = payload.status
    db.commit()
    log_event("product_status", client_ip=client_ip(request), by=claims["sub"], slug=slug, status=payload.status)
    return _product_out(drone)


@router.post("/api/admin/products/{slug}/image", dependencies=[Depends(require_admin)])
async def upload_image(slug: str, request: Request, claims: dict = Depends(require_admin),
                       db: Session = Depends(get_db)):
    """Send the photo as the request body with its Content-Type (image/jpeg, image/png or image/webp)."""
    drone = _drone_or_404(db, slug)
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    allowed = VULN_IMAGE_TYPES if settings.vuln_mode else IMAGE_TYPES
    ext = allowed.get(content_type)
    if ext is None:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG or WebP image.")
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="The upload is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="The image must be 2 MB or smaller.")
    if not settings.vuln_mode and not _image_matches(data, ext):
        raise HTTPException(status_code=415, detail="The file is not a valid image of that type.")

    target = settings.media_dir / "drones" / f"{drone.slug}{ext}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    # The timestamp makes browsers and NGINX fetch the new photo instead of a cached old one.
    drone.image_url = f"/api/media/drones/{drone.slug}{ext}?v={int(time.time())}"
    drone.manual_edit = True
    db.commit()
    log_event("product_image_uploaded", client_ip=client_ip(request), by=claims["sub"], slug=slug, bytes=len(data))
    return _product_out(drone)


# --------------------------------------------------------------------------- newsletters (staff write, admin sends)
@router.get("/api/admin/campaigns", dependencies=[Depends(require_staff)])
def list_campaigns(db: Session = Depends(get_db)):
    rows = db.scalars(select(Campaign).order_by(Campaign.id.desc()).limit(200)).all()
    return [_campaign_out(c) for c in rows]


@router.post("/api/admin/campaigns", status_code=201)
def create_campaign(payload: CampaignIn, claims: dict = Depends(require_staff), db: Session = Depends(get_db)):
    campaign = Campaign(subject=clean_text(payload.subject), body=clean_text(payload.body), author=claims["sub"])
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    log_event("campaign_created", by=claims["sub"], campaign_id=campaign.id)
    return _campaign_out(campaign)


@router.put("/api/admin/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, payload: CampaignIn, claims: dict = Depends(require_staff),
                    db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    if campaign.status == "sent":
        raise HTTPException(status_code=409, detail="A sent newsletter cannot be changed.")
    campaign.subject = clean_text(payload.subject)
    campaign.body = clean_text(payload.body)
    db.commit()
    log_event("campaign_updated", by=claims["sub"], campaign_id=campaign.id)
    return _campaign_out(campaign)


@router.post("/api/admin/campaigns/{campaign_id}/send", dependencies=[Depends(require_admin)])
def send_campaign(campaign_id: int, claims: dict = Depends(require_admin), db: Session = Depends(get_db)):
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Newsletter not found")
    if campaign.status == "sent":
        raise HTTPException(status_code=409, detail="This newsletter was already sent.")
    recipients = db.scalar(select(func.count()).select_from(Subscriber)) or 0
    campaign.status = "sent"
    campaign.recipients = recipients
    campaign.sent_at = datetime.now(timezone.utc)
    db.commit()
    log_event("newsletter_sent", by=claims["sub"], campaign_id=campaign.id, recipients=recipients)
    return _campaign_out(campaign)


# --------------------------------------------------------------------------- news articles
class ArticleIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=500)
    category: str
    body: str = Field(default="", max_length=50_000)


class ArticleStatusIn(BaseModel):
    status: str


def _article_out(p: Post) -> dict:
    return {
        "id": p.id,
        "slug": p.slug,
        "title": p.title,
        "summary": p.summary,
        "category": p.category,
        "author": p.author,
        "body": p.body,
        "status": p.status,
        "published_at": p.published_at.isoformat() if p.published_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def _article_or_404(db: Session, article_id: int) -> Post:
    post = db.get(Post, article_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return post


def _check_article(data: dict) -> dict:
    if data["category"] not in ARTICLE_CATEGORIES:
        raise HTTPException(status_code=422, detail=f"Category must be one of: {', '.join(ARTICLE_CATEGORIES)}.")
    return {k: (clean_text(v) if isinstance(v, str) else v) for k, v in data.items()}


@router.get("/api/admin/articles", dependencies=[Depends(require_staff)])
def list_articles(db: Session = Depends(get_db)):
    rows = db.scalars(select(Post).order_by(Post.status, Post.published_at.desc())).all()
    return [_article_out(p) for p in rows]


@router.post("/api/admin/articles", status_code=201)
def create_article(payload: ArticleIn, request: Request, claims: dict = Depends(require_staff),
                   db: Session = Depends(get_db)):
    fields = _check_article(payload.model_dump())
    base = slugify(fields["title"])
    slug, n = base, 2
    while db.scalar(select(Post).where(Post.slug == slug)) is not None:  # keep slugs unique
        slug, n = f"{base}-{n}", n + 1
    post = Post(slug=slug, author=claims["sub"], status="draft", **fields)
    db.add(post)
    db.commit()
    db.refresh(post)
    log_event("article_created", client_ip=client_ip(request), by=claims["sub"], article_id=post.id)
    return _article_out(post)


@router.put("/api/admin/articles/{article_id}", dependencies=[Depends(require_staff)])
def update_article(article_id: int, payload: ArticleIn, request: Request, claims: dict = Depends(require_staff),
                   db: Session = Depends(get_db)):
    post = _article_or_404(db, article_id)
    if post.status == "published" and claims.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only an admin can change a published article.")
    fields = _check_article(payload.model_dump())
    for field, value in fields.items():  # the link (slug) stays the same, so shared links keep working
        setattr(post, field, value)
    db.commit()
    log_event("article_updated", client_ip=client_ip(request), by=claims["sub"], article_id=post.id)
    return _article_out(post)


@router.post("/api/admin/articles/{article_id}/status", dependencies=[Depends(require_admin)])
def set_article_status(article_id: int, payload: ArticleStatusIn, request: Request,
                       claims: dict = Depends(require_admin), db: Session = Depends(get_db)):
    if payload.status not in ("published", "draft"):
        raise HTTPException(status_code=422, detail="Status must be published or draft.")
    post = _article_or_404(db, article_id)
    post.status = payload.status
    if payload.status == "published":
        post.published_at = datetime.now(timezone.utc)  # the date readers see is the day it went live
    db.commit()
    log_event("article_status", client_ip=client_ip(request), by=claims["sub"], article_id=post.id, status=post.status)
    return _article_out(post)


@router.delete("/api/admin/articles/{article_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_article(article_id: int, request: Request, claims: dict = Depends(require_admin),
                   db: Session = Depends(get_db)):
    post = _article_or_404(db, article_id)
    db.delete(post)
    db.commit()
    log_event("article_deleted", client_ip=client_ip(request), by=claims["sub"], article_id=article_id)
    return Response(status_code=204)
