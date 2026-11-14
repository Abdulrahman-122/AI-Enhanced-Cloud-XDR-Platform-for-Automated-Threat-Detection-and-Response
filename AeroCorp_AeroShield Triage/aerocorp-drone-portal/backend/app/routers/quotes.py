import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..logging_setup import log_event
from ..models import Drone, QuoteRequest
from ..security import bearer_claims, client_ip, customer_id_from, limiter
from ..util import EMAIL_RE, clean_text, flag_suspicious, out_text

router = APIRouter()


class QuoteIn(BaseModel):
    drone_slug: str
    contact_name: str
    email: str
    company: str = ""
    quantity: int = 1
    notes: str = ""


def _quote_out(q: QuoteRequest, drone_name: str | None) -> dict:
    return {
        "id": q.id,
        "reference": f"Q-{q.id:05d}",
        "drone_slug": q.drone_slug,
        "drone_name": drone_name,
        "company": out_text(q.company),
        "contact_name": out_text(q.contact_name),
        "email": out_text(q.email),
        "quantity": q.quantity,
        "notes": out_text(q.notes),
        "created_at": q.created_at.isoformat(),
    }


@router.post("/api/quotes", status_code=201)
def create_quote(payload: QuoteIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    data = payload.model_dump()
    flag_suspicious("/api/quotes", ip, contact_name=payload.contact_name, email=payload.email, company=payload.company, notes=payload.notes)

    if not settings.vuln_mode:
        if not limiter.allow(f"quote:{ip}", 10, 600):
            log_event("rate_limited", client_ip=ip, scope="quote")
            raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
        data = {k: (clean_text(v) if isinstance(v, str) else v) for k, v in data.items()}
        problems = []
        if not 1 <= len(data["contact_name"]) <= 80:
            problems.append("Name must be 1 to 80 characters.")
        if len(data["email"]) > 254 or not EMAIL_RE.match(data["email"]):
            problems.append("Enter a valid email address.")
        if len(data["company"]) > 120:
            problems.append("Company must be 120 characters or fewer.")
        if not 1 <= data["quantity"] <= 10000:
            problems.append("Quantity must be between 1 and 10000.")
        if len(data["notes"]) > 1000:
            problems.append("Notes must be 1000 characters or fewer.")
        if problems:
            raise HTTPException(status_code=422, detail=" ".join(problems))

    drone = db.scalar(select(Drone).where(Drone.slug == data["drone_slug"], Drone.status == "published"))
    if drone is None:
        raise HTTPException(status_code=404, detail="Drone not found")

    token = secrets.token_urlsafe(16)
    quote = QuoteRequest(
        drone_slug=drone.slug, company=data["company"], contact_name=data["contact_name"],
        email=data["email"], quantity=data["quantity"], notes=data["notes"], token=token,
        customer_id=customer_id_from(request),  # None for guests
    )
    db.add(quote)
    db.commit()
    log_event("quote_created", client_ip=ip, quote_id=quote.id, drone=drone.slug)
    return {"id": quote.id, "reference": f"Q-{quote.id:05d}", "token": token}


@router.get("/api/quotes/{quote_id}")
def get_quote(quote_id: int, request: Request, token: str = "", db: Session = Depends(get_db)):
    quote = db.get(QuoteRequest, quote_id)
    ip = client_ip(request)
    # Logged for every lookup, found or not: a run of misses from one address is an ID-enumeration (IDOR) attempt.
    log_event("quote_lookup", client_ip=ip, quote_id=quote_id, found=quote is not None, token_present=bool(token))
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")

    if not settings.vuln_mode:
        claims = bearer_claims(request)
        is_admin = bool(claims and claims.get("role") == "admin")
        is_owner = quote.customer_id is not None and customer_id_from(request) == quote.customer_id
        if not (is_admin or is_owner) and not (token and secrets.compare_digest(token, quote.token)):
            # Same answer as a missing quote, so ids cannot be probed.
            raise HTTPException(status_code=404, detail="Quote not found")

    drone = db.scalar(select(Drone).where(Drone.slug == quote.drone_slug))
    return _quote_out(quote, drone.name if drone else None)
