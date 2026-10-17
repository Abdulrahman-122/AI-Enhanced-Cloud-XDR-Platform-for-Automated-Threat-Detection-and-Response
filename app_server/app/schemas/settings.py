from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any


class DiagnosticsResponse(BaseModel):
    wazuh_connected: bool
    wazuh_endpoint: str
    wazuh_version: str
    status_message: str
    database_status: str
    app_version: str
    jwt_status: str
    timestamp: str


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
