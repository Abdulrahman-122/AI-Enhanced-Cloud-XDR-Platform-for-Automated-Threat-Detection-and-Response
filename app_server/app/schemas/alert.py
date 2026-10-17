from pydantic import BaseModel
from typing import Optional, List, Any


class AlertItem(BaseModel):
    id: str
    timestamp: str
    agent_id: str
    agent_name: str
    agent_ip: str
    rule_id: int
    rule_level: int
    rule_description: str
    rule_groups: Optional[List[str]] = []
    severity: str  # critical, high, medium, low
    source_ip: str
    destination_ip: Optional[str] = "-"
    destination_port: Optional[int] = 0
    protocol: Optional[str] = "TCP"
    location: str
    status: str
    mitre_tactic: Optional[str] = None
    mitre_technique_id: Optional[str] = None
    mitre_technique_name: Optional[str] = None
    raw_log: Optional[str] = None


class AlertListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[AlertItem]
