from fastapi import APIRouter, Depends
from app.services.wazuh_service import wazuh_service
from app.schemas.dashboard import DashboardResponse
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/dashboard", tags=["XDR Dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Get XDR Security Dashboard Overview",
    description="Returns aggregated metrics, active/disconnected agents, severity counts, timeline charts, top detection rules, and live Wazuh connection status."
)
async def get_dashboard_data(current_user: User = Depends(get_current_user)):
    data = await wazuh_service.get_dashboard_summary()
    return data
