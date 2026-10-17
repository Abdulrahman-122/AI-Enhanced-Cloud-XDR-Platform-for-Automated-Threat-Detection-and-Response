from pydantic import BaseModel
from typing import List, Optional


class MitreTechnique(BaseModel):
    id: str
    name: str
    count: int
    severity: str


class MitreTactic(BaseModel):
    id: str
    name: str
    event_count: int
    techniques: List[MitreTechnique]


class FimEvent(BaseModel):
    id: str
    timestamp: str
    agent_name: str
    file_path: str
    event_type: str
    user: str
    md5_before: str
    md5_after: str
    severity: str


class VulnerabilityItem(BaseModel):
    cve_id: str
    package: str
    agent_name: str
    severity: str
    description: str
    status: str


class ThreatIntelResponse(BaseModel):
    mitre_tactics: List[MitreTactic]
    fim_events: List[FimEvent]
    vulnerabilities: List[VulnerabilityItem]
    last_updated: str
