from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..logging_setup import log_event
from ..models import ContactMessage
from ..security import client_ip, limiter
from ..util import EMAIL_RE, clean_text, flag_suspicious

router = APIRouter()


class ContactIn(BaseModel):
    name: str
    email: str
    subject: str = ""
    message: str
    website: str = ""  # honeypot: real visitors never see or fill this field


@router.post("/api/contact", status_code=201)
def submit_contact(payload: ContactIn, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    data = payload.model_dump()
    flag_suspicious("/api/contact", ip, name=payload.name, email=payload.email, subject=payload.subject, message=payload.message)

    if not settings.vuln_mode:
        if not limiter.allow(f"contact:{ip}", 5, 600):
            log_event("rate_limited", client_ip=ip, scope="contact")
            raise HTTPException(status_code=429, detail="Too many messages. Please try again later.")
        if payload.website:
            log_event("honeypot_triggered", client_ip=ip, scope="contact")
            return {"ok": True}
        data = {k: clean_text(v) for k, v in data.items()}
        problems = []
        if not 1 <= len(data["name"]) <= 80:
            problems.append("Name must be 1 to 80 characters.")
        if len(data["email"]) > 254 or not EMAIL_RE.match(data["email"]):
            problems.append("Enter a valid email address.")
        if len(data["subject"]) > 120:
            problems.append("Subject must be 120 characters or fewer.")
        if not 5 <= len(data["message"]) <= 2000:
            problems.append("Message must be 5 to 2000 characters.")
        if problems:
            raise HTTPException(status_code=422, detail=" ".join(problems))

    record = ContactMessage(
        name=data["name"], email=data["email"], subject=data["subject"], message=data["message"], ip=ip
    )
    db.add(record)
    db.commit()
    log_event("contact_submitted", client_ip=ip, message_id=record.id, length=len(data["message"]))
    return {"ok": True, "id": record.id} if settings.vuln_mode else {"ok": True}
