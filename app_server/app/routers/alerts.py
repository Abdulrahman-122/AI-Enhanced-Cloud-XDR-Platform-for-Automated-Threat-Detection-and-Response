from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.services.wazuh_service import wazuh_service
from app.schemas.alert import AlertListResponse, AlertItem
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/alerts", tags=["Security Alerts"])


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List Security Alerts and Incident Events",
    description="Retrieve paginated security alerts with filtering by severity level, agent, search keywords, and date ranges."
)
async def list_alerts(
    severity: Optional[str] = Query(None, description="Severity filter: critical, high, medium, low, all"),
    agent_id: Optional[str] = Query(None, description="Agent ID filter"),
    search: Optional[str] = Query(None, description="Keyword search in rule description, ID, IP, MITRE tactic"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    return await wazuh_service.get_alerts(
        limit=limit,
        offset=offset,
        severity=severity,
        agent_id=agent_id,
        search=search
    )


@router.get(
    "/{alert_id}",
    response_model=AlertItem,
    summary="Get Alert Detail by ID",
    description="Fetch single alert complete event metadata and raw log."
)
async def get_alert_detail(
    alert_id: str,
    current_user: User = Depends(get_current_user)
):
    alerts_data = await wazuh_service.get_alerts(limit=200)
    for al in alerts_data.get("items", []):
        if al.get("id") == alert_id:
            return al
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Security alert '{alert_id}' not found."
    )
