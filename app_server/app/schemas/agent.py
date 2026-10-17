from pydantic import BaseModel
from typing import Optional, List, Any


class AgentItem(BaseModel):
    id: str
    name: str
    ip: str
    os: str
    version: str
    status: str
    last_keepalive: str
    group: Optional[str] = "default"
    node_name: Optional[str] = None


class AgentDetail(AgentItem):
    syscheck_enabled: Optional[bool] = True
    rootcheck_enabled: Optional[bool] = True
    open_ports: Optional[List[int]] = []
    cpu_usage: Optional[str] = None
    memory_usage: Optional[str] = None
    disk_usage: Optional[str] = None
    os_architecture: Optional[str] = None
    last_scan: Optional[str] = None


class AgentListResponse(BaseModel):
    total: int
    items: List[AgentItem]
    source: str
