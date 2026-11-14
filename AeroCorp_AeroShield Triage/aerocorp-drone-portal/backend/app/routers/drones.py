from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Drone
from ..seed_data import CATEGORIES

router = APIRouter()

SORTS = {
    "name": lambda: Drone.name.asc(),
    "price": lambda: Drone.price_usd.asc().nulls_last(),
    "newest": lambda: Drone.id.desc(),
}


def drone_out(d: Drone, detail: bool = False) -> dict:
    out = {
        "id": d.id,
        "slug": d.slug,
        "name": d.name,
        "manufacturer": d.manufacturer,
        "category": d.category,
        "description": d.description,
        "price_usd": d.price_usd,
        "image_url": d.image_url,
        "specs": d.specs or {},
    }
    if detail:
        out.update(
            image_credit=d.image_credit,
            source_url=d.source_url,
            datasheet_url=f"/api/datasheets/download?file={d.slug}.txt",
        )
    return out


@router.get("/api/categories")
def categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Drone.category, func.count()).where(Drone.status == "published").group_by(Drone.category)
    ).all()
    order = {name: i for i, name in enumerate(CATEGORIES)}
    rows.sort(key=lambda r: order.get(r[0], 99))
    return [{"name": name, "count": count} for name, count in rows]


@router.get("/api/drones")
def list_drones(
    category: str | None = None,
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(12, ge=1, le=50),
    sort: str = "name",
    db: Session = Depends(get_db),
):
    stmt = select(Drone).where(Drone.status == "published")
    if category:
        stmt = stmt.where(Drone.category == category)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = SORTS.get(sort, SORTS["name"])()
    rows = db.scalars(stmt.order_by(order, Drone.id).offset((page - 1) * limit).limit(limit)).all()
    return {
        "items": [drone_out(d) for d in rows],
        "total": total,
        "page": page,
        "pages": max(1, ceil(total / limit)),
    }


@router.get("/api/drones/{slug}")
def drone_detail(slug: str, db: Session = Depends(get_db)):
    drone = db.scalar(select(Drone).where(Drone.slug == slug, Drone.status == "published"))
    if drone is None:  # unpublished (pending review) aircraft look exactly like missing ones
        raise HTTPException(status_code=404, detail="Drone not found")
    related = db.scalars(
        select(Drone)
        .where(Drone.category == drone.category, Drone.id != drone.id, Drone.status == "published")
        .order_by(Drone.name).limit(3)
    ).all()
    return {**drone_out(drone, detail=True), "related": [drone_out(r) for r in related]}
