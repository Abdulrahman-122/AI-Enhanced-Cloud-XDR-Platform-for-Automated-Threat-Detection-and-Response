from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Post

router = APIRouter()


def post_out(p: Post, detail: bool = False) -> dict:
    out = {
        "id": p.id,
        "slug": p.slug,
        "title": p.title,
        "summary": p.summary,
        "category": p.category,
        "author": p.author,
        "published_at": p.published_at.isoformat(),
    }
    if detail:
        out["body"] = p.body
    return out


@router.get("/api/posts")
def list_posts(page: int = Query(1, ge=1, le=1000), limit: int = Query(9, ge=1, le=30), db: Session = Depends(get_db)):
    visible = Post.status == "published"
    total = db.scalar(select(func.count()).select_from(Post).where(visible)) or 0
    rows = db.scalars(select(Post).where(visible).order_by(Post.published_at.desc()).offset((page - 1) * limit).limit(limit)).all()
    return {"items": [post_out(p) for p in rows], "total": total, "page": page, "pages": max(1, ceil(total / limit))}


@router.get("/api/posts/{slug}")
def get_post(slug: str, db: Session = Depends(get_db)):
    post = db.scalar(select(Post).where(Post.slug == slug, Post.status == "published"))
    if post is None:  # drafts look exactly like missing articles
        raise HTTPException(status_code=404, detail="Article not found")
    return post_out(post, detail=True)
