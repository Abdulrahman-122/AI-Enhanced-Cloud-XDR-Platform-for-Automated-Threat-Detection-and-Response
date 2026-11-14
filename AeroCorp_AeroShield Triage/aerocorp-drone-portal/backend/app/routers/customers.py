from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..logging_setup import log_event
from ..models import Customer, Drone, Favorite, QuoteRequest
from ..security import (DUMMY_HASH, client_ip, create_token, hash_password, limiter, require_customer,
                        verify_password)
from ..util import EMAIL_RE, clean_text, flag_suspicious

router = APIRouter(prefix="/api/customers")

LOCKOUT_FAILURES = 5
LOCKOUT_WINDOW = 900  # seconds


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str
    company: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileIn(BaseModel):
    name: str
    company: str = ""


def _session_out(customer: Customer) -> dict:
    return {
        "token": create_token(str(customer.id), "customer"),
        "role": "customer",
        "username": customer.name,
        "name": customer.name,
        "email": customer.email,
        "company": customer.company,
        "expires_in": settings.token_ttl_seconds,
    }


def _profile(customer: Customer) -> dict:
    return {"id": customer.id, "name": customer.name, "email": customer.email, "company": customer.company,
            "created_at": customer.created_at.isoformat()}


def _check_profile(name: str, company: str) -> tuple[str, str]:
    name, company = clean_text(name), clean_text(company)
    problems = []
    if not 1 <= len(name) <= 80:
        problems.append("Name must be 1 to 80 characters.")
    if len(company) > 120:
        problems.append("Company must be 120 characters or fewer.")
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))
    return name, company


@router.post("/register", status_code=201)
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    flag_suspicious("/api/customers/register", ip, name=payload.name, email=payload.email, company=payload.company)
    email = payload.email.strip().lower()

    if not settings.vuln_mode:
        if not limiter.allow(f"register:{ip}", 5, 3600):
            log_event("rate_limited", client_ip=ip, scope="register")
            raise HTTPException(status_code=429, detail="Too many registrations from this address. Try again later.")
        name, company = _check_profile(payload.name, payload.company)
        problems = []
        if len(email) > 254 or not EMAIL_RE.match(email):
            problems.append("Enter a valid email address.")
        if not 8 <= len(payload.password) <= 128:
            problems.append("Password must be 8 to 128 characters.")
        if problems:
            raise HTTPException(status_code=422, detail=" ".join(problems))
    else:
        name, company = payload.name.strip(), payload.company.strip()

    if db.scalar(select(Customer).where(Customer.email == email)) is not None:
        log_event("account_exists", client_ip=ip, account="customer")
        if settings.vuln_mode:  # enumeration: the answer reveals that this email has an account
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        raise HTTPException(status_code=400, detail="We could not create that account. If you already have one, sign in instead.")

    customer = Customer(email=email, name=name or payload.name, company=company,
                        password_hash=hash_password(payload.password))
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:  # two registrations for the same email at the same moment
        db.rollback()
        raise HTTPException(status_code=400, detail="We could not create that account. If you already have one, sign in instead.")
    log_event("account_created", client_ip=ip, customer_id=customer.id)
    return _session_out(customer)


@router.post("/login")
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    email = payload.email.strip().lower()[:254]
    flag_suspicious("/api/customers/login", ip, email=payload.email)
    fail_key = f"cfail:{email}"

    if not settings.vuln_mode:
        if not limiter.allow(f"clogin-ip:{ip}", 10, 300):
            log_event("rate_limited", client_ip=ip, scope="customer-login")
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in a few minutes.",
                                headers={"Retry-After": "300"})
        if limiter.count(fail_key, LOCKOUT_WINDOW) >= LOCKOUT_FAILURES:
            log_event("account_locked", client_ip=ip, username=email[:64], account="customer")
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in a few minutes.",
                                headers={"Retry-After": "900"})

    customer = db.scalar(select(Customer).where(Customer.email == email))
    if customer is None:
        if not settings.vuln_mode:
            verify_password(payload.password, DUMMY_HASH)
            limiter.record(fail_key)
        log_event("auth_failed", client_ip=ip, username=email[:64], reason="unknown_user", account="customer")
        raise HTTPException(status_code=401, detail="No account with that email" if settings.vuln_mode
                            else "Invalid email or password.")

    if not verify_password(payload.password, customer.password_hash):
        if not settings.vuln_mode:
            limiter.record(fail_key)
        log_event("auth_failed", client_ip=ip, username=email[:64], reason="wrong_password", account="customer")
        raise HTTPException(status_code=401, detail="Incorrect password" if settings.vuln_mode
                            else "Invalid email or password.")

    limiter.clear(fail_key)
    log_event("auth_success", client_ip=ip, username=customer.email, role="customer", customer_id=customer.id)
    return _session_out(customer)


def _customer(db: Session, request: Request) -> Customer:
    customer = db.get(Customer, require_customer(request))
    if customer is None:  # token for an account that was deleted
        raise HTTPException(status_code=401, detail="Sign in to your account first.")
    return customer


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    return _profile(_customer(db, request))


@router.put("/me")
def update_me(payload: ProfileIn, request: Request, db: Session = Depends(get_db)):
    customer = _customer(db, request)
    customer.name, customer.company = _check_profile(payload.name, payload.company)
    db.commit()
    return _profile(customer)


@router.get("/me/favorites")
def favorites(request: Request, db: Session = Depends(get_db)):
    customer = _customer(db, request)
    rows = db.execute(
        select(Drone)
        .join(Favorite, Favorite.drone_id == Drone.id)
        .where(Favorite.customer_id == customer.id, Drone.status == "published")
        .order_by(Favorite.created_at.desc())
    ).scalars().all()
    return [
        {"slug": d.slug, "name": d.name, "manufacturer": d.manufacturer, "category": d.category,
         "image_url": d.image_url, "price_usd": d.price_usd}
        for d in rows
    ]


@router.post("/me/favorites/{slug}", status_code=201)
def add_favorite(slug: str, request: Request, db: Session = Depends(get_db)):
    customer = _customer(db, request)
    drone = db.scalar(select(Drone).where(Drone.slug == slug, Drone.status == "published"))
    if drone is None:
        raise HTTPException(status_code=404, detail="Aircraft not found")
    exists = db.scalar(select(Favorite).where(Favorite.customer_id == customer.id, Favorite.drone_id == drone.id))
    if exists is None:
        db.add(Favorite(customer_id=customer.id, drone_id=drone.id))
        db.commit()
    return {"slug": drone.slug, "saved": True}


@router.delete("/me/favorites/{slug}", status_code=204)
def remove_favorite(slug: str, request: Request, db: Session = Depends(get_db)):
    customer = _customer(db, request)
    drone = db.scalar(select(Drone).where(Drone.slug == slug))
    if drone is not None:
        db.query(Favorite).filter(Favorite.customer_id == customer.id, Favorite.drone_id == drone.id).delete()
        db.commit()
    return Response(status_code=204)


@router.get("/me/quotes")
def my_quotes(request: Request, db: Session = Depends(get_db)):
    customer = _customer(db, request)
    rows = db.scalars(
        select(QuoteRequest).where(QuoteRequest.customer_id == customer.id).order_by(QuoteRequest.id.desc())
    ).all()
    names = {d.slug: d.name for d in db.scalars(select(Drone).where(Drone.slug.in_([q.drone_slug for q in rows] or [""])))}
    return [
        {"id": q.id, "reference": f"Q-{q.id:05d}", "drone_slug": q.drone_slug,
         "drone_name": names.get(q.drone_slug), "quantity": q.quantity, "created_at": q.created_at.isoformat()}
        for q in rows
    ]
