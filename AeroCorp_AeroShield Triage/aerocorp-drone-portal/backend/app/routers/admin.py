from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ContactMessage, Drone, Post, QuoteRequest, Subscriber, User
from ..security import require_admin
from ..util import out_text

router = APIRouter(prefix="/api/admin", dependencies=[Depends(require_admin)])


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    def count(model):
        return db.scalar(select(func.count()).select_from(model)) or 0

    return {
        "drones": count(Drone),
        "posts": count(Post),
        "subscribers": count(Subscriber),
        "messages": count(ContactMessage),
        "quotes": count(QuoteRequest),
        "users": count(User),
    }


@router.get("/messages")
def messages(db: Session = Depends(get_db)):
    rows = db.scalars(select(ContactMessage).order_by(ContactMessage.id.desc()).limit(200)).all()
    return [
        {
            "id": m.id,
            "name_html": out_text(m.name),
            "email_html": out_text(m.email),
            "subject_html": out_text(m.subject),
            "message_html": out_text(m.message),
            "ip": m.ip,
            "created_at": m.created_at.isoformat(),
        }
        for m in rows
    ]


@router.get("/subscribers")
def subscribers(db: Session = Depends(get_db)):
    rows = db.scalars(select(Subscriber).order_by(Subscriber.id.desc()).limit(500)).all()
    return [{"id": s.id, "email": s.email, "ip": s.ip, "created_at": s.created_at.isoformat()} for s in rows]


@router.get("/quotes")
def quotes(db: Session = Depends(get_db)):
    rows = db.scalars(select(QuoteRequest).order_by(QuoteRequest.id.desc()).limit(200)).all()
    return [
        {
            "id": q.id,
            "reference": f"Q-{q.id:05d}",
            "drone_slug": q.drone_slug,
            "company": out_text(q.company),
            "contact_name": out_text(q.contact_name),
            "email": out_text(q.email),
            "quantity": q.quantity,
            "created_at": q.created_at.isoformat(),
        }
        for q in rows
    ]
