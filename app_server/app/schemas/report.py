from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class ReportSummaryResponse(BaseModel):
    generated_at: str
    organization: str
    project_title: str
    total_events_analyzed: int
    agents_monitored: int
    critical_incidents: int
    resolved_incidents: int
    compliance_score: float
    threat_overview: Dict[str, Any]
    severity_breakdown: Dict[str, int]
    top_affected_assets: List[Dict[str, Any]]
