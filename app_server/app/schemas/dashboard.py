from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.schemas.alert import AlertItem
from app.schemas.wazuh import WazuhStatusResponse


class AlertsOverTimeItem(BaseModel):
    time: str
    critical: int
    high: int
    medium: int
    low: int


class SeverityDistributionItem(BaseModel):
    name: str
    value: int
    color: str


class AlertsByAgentItem(BaseModel):
    agent: str
    alerts: int


class TopRuleItem(BaseModel):
    rule_id: int
    description: str
    count: int
    level: int
    severity: str


class TopThreatCategoryItem(BaseModel):
    category: str
    count: int
    percentage: float


class DashboardResponse(BaseModel):
    total_agents: int
    active_agents: int
    disconnected_agents: int
    pending_agents: int
    total_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    alerts_over_time: List[AlertsOverTimeItem]
    alerts_by_severity: List[SeverityDistributionItem]
    alerts_by_agent: List[AlertsByAgentItem]
    top_rules: List[TopRuleItem]
    top_threat_categories: List[TopThreatCategoryItem]
    recent_alerts: List[AlertItem]
    wazuh_status: WazuhStatusResponse
    last_updated: str
