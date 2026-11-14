import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import Base, SessionLocal, engine, ensure_schema, wait_for_db
from .logging_setup import log_event, setup_logging
from .routers import admin, auth, contact, customers, drones, files, misc, newsletter, posts, quotes, search, staff
from .security import client_ip, limiter
from .seed import seed_if_empty

setup_logging()
settings.media_dir.mkdir(parents=True, exist_ok=True)
settings.datasheet_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    wait_for_db()
    Base.metadata.create_all(engine)
    ensure_schema()
    with SessionLocal() as db:
        added = seed_if_empty(db)
    log_event("startup", seeded=added)
    yield


app = FastAPI(
    title="AeroCorp Drone Portal",
    version="1.0.0",
    lifespan=lifespan,
    # Exposed API docs are a realistic finding in the weak build, and handy for importing into Burp.
    docs_url="/api/docs" if settings.vuln_mode else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.vuln_mode else None,
)

if settings.vuln_mode:
    # Wildcard CORS is a deliberate misconfiguration for the lab.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HARDENED_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def observe(request: Request, call_next):
    started = time.perf_counter()
    ip = client_ip(request)
    path = request.scope["path"]
    response = None

    if not settings.vuln_mode and path.startswith("/api/") and not limiter.allow(f"global:{ip}", 240, 60):
        log_event("rate_limited", client_ip=ip, scope="global", path=path)
        response = JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"})

    if response is None:
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            log_event("unhandled_error", client_ip=ip, path=path, error=repr(exc)[:500])
            body = {"detail": "Internal server error"}
            if settings.vuln_mode:  # verbose errors are part of the lab weakness
                body.update(error=repr(exc), trace=traceback.format_exc())
            response = JSONResponse(body, status_code=500)

    if not settings.vuln_mode and path.startswith("/api/") and not path.startswith("/api/media"):
        for key, value in HARDENED_HEADERS.items():
            response.headers.setdefault(key, value)

    log_event(
        "http_request",
        client_ip=ip,
        method=request.method,
        path=path,
        query=request.scope.get("query_string", b"").decode("latin-1"),
        status=response.status_code,
        user_agent=request.headers.get("user-agent", "")[:300],
        referrer=request.headers.get("referer", "")[:300],
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )
    return response


for module in (misc, drones, posts, search, contact, newsletter, auth, customers, quotes, files, admin, staff):
    app.include_router(module.router)

app.mount("/api/media", StaticFiles(directory=str(settings.media_dir)), name="media")
