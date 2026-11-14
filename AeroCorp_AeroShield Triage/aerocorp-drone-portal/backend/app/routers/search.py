from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db, run_raw_readonly
from ..logging_setup import log_event
from ..models import Drone, Post
from ..security import client_ip, limiter
from ..seed_data import CATEGORIES
from ..util import escape_like, flag_suspicious, out_text
from .drones import drone_out
from .posts import post_out

router = APIRouter()

DRONE_COLUMNS = "id, slug, name, manufacturer, category, description, image_url"


def _empty(q: str):
    return {"query": q, "query_display": out_text(q), "count": 0, "drones": [], "posts": []}


@router.get("/api/search")
def search(request: Request, q: str = "", category: str = "", db: Session = Depends(get_db)):
    ip = client_ip(request)
    flag_suspicious("/api/search", ip, q=q, category=category)

    if not q.strip():
        return _empty(q)

    if settings.vuln_mode:
        sql = (
            f"SELECT {DRONE_COLUMNS} FROM drones "
            f"WHERE status = 'published' AND (name ILIKE '%{q}%' OR description ILIKE '%{q}%' OR manufacturer ILIKE '%{q}%')"
        )
        if category:
            sql += f" AND category = '{category}'"
        sql += " ORDER BY name"
        try:
            columns, rows = run_raw_readonly(sql)
        except Exception as exc:  # noqa: BLE001 - verbose error is the point of the lab weakness
            log_event("db_error", client_ip=ip, path="/api/search", error=str(exc)[:500])
            return JSONResponse(
                status_code=500,
                content={"detail": "Database error", "error": str(exc), "query": sql},
            )
        drones = [jsonable_encoder(dict(zip(columns, row))) for row in rows]
        post_pattern = f"%{q}%"
    else:
        if not limiter.allow(f"search:{ip}", 30, 60):
            log_event("rate_limited", client_ip=ip, scope="search")
            raise HTTPException(status_code=429, detail="Too many searches. Try again in a minute.")
        q = q.strip()
        if len(q) > 80:
            raise HTTPException(status_code=422, detail="Search text is limited to 80 characters.")
        pattern = f"%{escape_like(q)}%"
        stmt = select(Drone).where(Drone.status == "published").where(
            or_(
                Drone.name.ilike(pattern, escape="\\"),
                Drone.description.ilike(pattern, escape="\\"),
                Drone.manufacturer.ilike(pattern, escape="\\"),
            )
        )
        if category in CATEGORIES:
            stmt = stmt.where(Drone.category == category)
        drones = [
            {k: v for k, v in drone_out(d).items() if k in DRONE_COLUMNS.replace(" ", "").split(",")}
            for d in db.scalars(stmt.order_by(Drone.name).limit(50))
        ]
        post_pattern = pattern

    post_stmt = select(Post).where(Post.status == "published").where(
        or_(Post.title.ilike(post_pattern, escape="\\"), Post.summary.ilike(post_pattern, escape="\\"))
    )
    posts = [post_out(p) for p in db.scalars(post_stmt.order_by(Post.published_at.desc()).limit(20))]

    return {
        "query": q,
        "query_display": out_text(q),
        "count": len(drones) + len(posts),
        "drones": drones,
        "posts": posts,
    }
