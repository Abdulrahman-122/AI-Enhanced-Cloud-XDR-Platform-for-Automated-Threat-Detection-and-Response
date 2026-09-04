from pydantic import BaseModel
from typing import Optional


class WazuhStatusResponse(BaseModel):
    connected: bool
    url: str
    version: str
    status_message: str
    timestamp: str
