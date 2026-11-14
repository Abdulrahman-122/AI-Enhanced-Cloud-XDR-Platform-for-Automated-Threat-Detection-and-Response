from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..logging_setup import log_event
from ..models import Subscriber
from ..security import client_ip, limiter
from ..util import EMAIL_RE, clean_text, flag_suspicious

router = APIRouter()


class NewsletterIn(BaseModel):
    email: str


@router.post("/api/newsletter", status_code=201)
def subscribe(payload: NewsletterIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    email = payload.email
    flag_suspicious("/api/newsletter", ip, email=email)

    if settings.vuln_mode:
        if db.scalar(select(Subscriber).where(Subscriber.email == email)):
            raise HTTPException(status_code=409, detail="That email is already subscribed")
    else:
        if not limiter.allow(f"newsletter:{ip}", 5, 600):
            log_event("rate_limited", client_ip=ip, scope="newsletter")
            raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")
        email = clean_text(email).lower()
        if len(email) > 254 or not EMAIL_RE.match(email):
            raise HTTPException(status_code=422, detail="Enter a valid email address.")
        if db.scalar(select(Subscriber).where(Subscriber.email == email)):
            return {"ok": True, "message": "Check your inbox to confirm your subscription."}

    try:
        db.add(Subscriber(email=email, ip=ip))
        db.commit()
    except IntegrityError:
        db.rollback()
    log_event("newsletter_subscribed", client_ip=ip)
    return {"ok": True, "message": "Check your inbox to confirm your subscription."}
