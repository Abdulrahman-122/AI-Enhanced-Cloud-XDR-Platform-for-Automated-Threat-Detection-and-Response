from app.routers.auth import router as auth_router
from app.routers.home import router as home_router
from app.routers.dashboard import router as dashboard_router
from app.routers.agents import router as agents_router
from app.routers.alerts import router as alerts_router
from app.routers.threats import router as threats_router
from app.routers.reports import router as reports_router
from app.routers.settings import router as settings_router

__all__ = [
    "auth_router",
    "home_router",
    "dashboard_router",
    "agents_router",
    "alerts_router",
    "threats_router",
    "reports_router",
    "settings_router"
]
