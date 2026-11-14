import time

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

_engine_ro = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Add the columns this version needs to tables created by an older version.

    `create_all()` creates new tables but never adds columns to existing ones, so an existing lab
    database would otherwise fail on the new `status` and `customer_id` columns. Idempotent.
    """
    statements = [
        "ALTER TABLE drones ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'published'",
        "CREATE INDEX IF NOT EXISTS ix_drones_status ON drones (status)",
        "ALTER TABLE drones ADD COLUMN IF NOT EXISTS manual_edit BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE posts ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'published'",
        "CREATE INDEX IF NOT EXISTS ix_posts_status ON posts (status)",
        "ALTER TABLE posts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
        "ALTER TABLE quote_requests ADD COLUMN IF NOT EXISTS customer_id INTEGER "
        "REFERENCES customers(id) ON DELETE SET NULL",
        "CREATE INDEX IF NOT EXISTS ix_quote_requests_customer_id ON quote_requests (customer_id)",
    ]
    with engine.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))


def wait_for_db(retries: int = 30, delay: float = 1.0) -> None:
    """Block until PostgreSQL accepts connections (useful right after `docker compose up`)."""
    last_error = None
    for _ in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(delay)
    raise RuntimeError(f"Database not reachable after {retries} attempts: {last_error}")


def run_raw_readonly(sql: str):
    """Run a hand-built SQL string and return (column_names, rows).

    Only the intentionally vulnerable search uses this. The statement runs through a SELECT-only
    connection with a short statement timeout, so injected SQL can read tables and use pg_sleep()
    (error-based, UNION and time-based techniques all work) but cannot write or drop anything.
    """
    global _engine_ro
    if _engine_ro is None:
        _engine_ro = create_engine(
            settings.database_url_ro or settings.database_url,
            pool_pre_ping=True,
            connect_args={"options": "-c statement_timeout=8000"},
        )
    conn = _engine_ro.raw_connection()
    try:
        cur = conn.cursor()
        if not settings.database_url_ro:
            # No dedicated read-only role configured: fall back to a read-only transaction.
            cur.execute("SET TRANSACTION READ ONLY")
        # No second argument on purpose: psycopg2 then leaves '%' in the SQL text alone.
        cur.execute(sql)
        if cur.description:
            columns = [col.name for col in cur.description]
            rows = cur.fetchall()
        else:
            columns, rows = [], []
        return columns, rows
    finally:
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        conn.close()
