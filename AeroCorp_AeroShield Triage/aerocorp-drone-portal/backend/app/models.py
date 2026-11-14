from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="sales")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Drone(Base):
    __tablename__ = "drones"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    manufacturer: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    specs: Mapped[dict] = mapped_column(JSON, default=dict)
    price_usd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_credit: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    wiki_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # "published" appears on the website. "pending" waits in the admin review queue (new scraped products).
    status: Mapped[str] = mapped_column(String(16), default="published", index=True)
    # Set when an admin edits the aircraft by hand. Scraper runs never overwrite a hand-edited aircraft.
    manual_edit: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Customer(Base):
    """A website customer (not staff). Passwords are stored as PBKDF2 hashes in both builds."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    company: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Favorite(Base):
    """Aircraft a customer saved to their account."""

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("customer_id", "drone_id", name="uq_favorite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    drone_id: Mapped[int] = mapped_column(ForeignKey("drones.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(60), default="News")
    author: Mapped[str] = mapped_column(String(80), default="AeroCorp Editorial")
    # "published" appears on the News pages. "draft" is visible only to staff.
    status: Mapped[str] = mapped_column(String(16), default="published", index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Campaign(Base):
    """A newsletter written by staff. Drafts can be edited; only an admin can send one."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)  # draft | sent
    author: Mapped[str] = mapped_column(String(64), default="")
    recipients: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Text columns on purpose: the weak build accepts input of any length.
    name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text, default="")
    message: Mapped[str] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    handled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class QuoteRequest(Base):
    __tablename__ = "quote_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    drone_slug: Mapped[str] = mapped_column(String(160), index=True)
    company: Mapped[str] = mapped_column(Text, default="")
    contact_name: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    token: Mapped[str] = mapped_column(String(64))
    # Set when a signed-in customer requests the quote, so it shows up in their account.
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
