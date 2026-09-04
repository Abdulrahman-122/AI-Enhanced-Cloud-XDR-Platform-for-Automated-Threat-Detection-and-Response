from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import (
    auth_router,
    home_router,
    dashboard_router,
    agents_router,
    alerts_router,
    threats_router,
    reports_router,
    settings_router
)
# Ensure models are imported so Base metadata knows all tables
import app.models.user


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    try:
        Base.metadata.create_all(bind=engine)
        print(">> [XDR Backend] Database tables initialized successfully.")
    except Exception as e:
        print(f">> [XDR Backend] Notice: Could not automatically connect/create tables: {e}")
        print(">> Ensure your database is running and DATABASE_URL is configured in .env")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise XDR Security Platform Backend for El Shorouk Academy Graduation Project. Features JWT Authentication, Live Wazuh SIEM/EDR Integration, MITRE ATT&CK Telemetry, and Threat Intelligence.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include Routers
app.include_router(auth_router)
app.include_router(home_router)
app.include_router(dashboard_router)
app.include_router(agents_router)
app.include_router(alerts_router)
app.include_router(threats_router)
app.include_router(reports_router)
app.include_router(settings_router)


@app.get("/", tags=["General"], summary="API Root Overview")
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "academy": "El Shorouk Academy",
        "project": "XDR Security Platform Graduation Project",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "auth_register": "POST /api/auth/register",
            "auth_login": "POST /api/auth/login",
            "user_profile": "GET /api/home/me",
            "dashboard_stats": "GET /api/dashboard",
            "agents_list": "GET /api/agents",
            "agent_detail": "GET /api/agents/{agent_id}",
            "alerts_list": "GET /api/alerts",
            "alert_detail": "GET /api/alerts/{alert_id}",
            "threat_intelligence": "GET /api/threats",
            "reports_summary": "GET /api/reports/summary",
            "reports_export_csv": "GET /api/reports/export/alerts.csv",
            "settings_diagnostics": "GET /api/settings/diagnostics",
            "settings_profile": "PUT /api/settings/profile",
            "health": "GET /api/health"
        }
    }


@app.get("/api/health", tags=["General"], summary="Health Check")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "academy": "El Shorouk Academy"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
