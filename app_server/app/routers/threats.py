from fastapi import APIRouter, Depends
from app.services.wazuh_service import wazuh_service
from app.schemas.threat import ThreatIntelResponse
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/threats", tags=["Threat Detection"])


@router.get(
    "",
    response_model=ThreatIntelResponse,
    summary="Get Threat Detection & MITRE ATT&CK Matrix",
    description="Retrieves MITRE ATT&CK tactics, File Integrity Monitoring (FIM / Syscheck) events, and Vulnerability Detector telemetry."
)
async def get_threat_intel(current_user: User = Depends(get_current_user)):
    return await wazuh_service.get_threat_intelligence()
