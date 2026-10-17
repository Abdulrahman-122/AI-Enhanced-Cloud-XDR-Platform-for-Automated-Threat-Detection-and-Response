from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional
from app.services.wazuh_service import wazuh_service
from app.schemas.agent import AgentListResponse, AgentDetail
from app.auth.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/agents", tags=["Wazuh Agents"])


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List Wazuh Monitored Agents",
    description="Retrieves list of connected and offline endpoints with status filtering and search capabilities."
)
async def list_agents(
    status: Optional[str] = Query(None, description="Filter by status (active, disconnected, pending, all)"),
    search: Optional[str] = Query(None, description="Search query matching agent name, IP, ID, OS"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user)
):
    return await wazuh_service.get_agents(status=status, search=search, limit=limit, offset=offset)


@router.get(
    "/{agent_id}",
    response_model=AgentDetail,
    summary="Get Detailed Agent Information",
    description="Returns full telemetry, open ports, resource usage, and security scan status for a given agent."
)
async def get_agent_detail(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    agent = await wazuh_service.get_agent_by_id(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID '{agent_id}' not found."
        )
    return agent
