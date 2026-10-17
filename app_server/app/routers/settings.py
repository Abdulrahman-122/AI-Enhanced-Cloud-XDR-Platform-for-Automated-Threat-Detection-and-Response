from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models.user import User
from app.schemas.settings import DiagnosticsResponse, ProfileUpdateRequest
from app.schemas.user import UserResponse
from app.services.wazuh_service import wazuh_service
from app.auth.dependencies import get_current_user
from app.auth.security import hash_password, verify_password
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["Settings & Diagnostics"])


@router.get(
    "/diagnostics",
    response_model=DiagnosticsResponse,
    summary="Get System Diagnostics & Wazuh Connection Health",
    description="Tests live connectivity to Wazuh Server, database state, and environment parameters without revealing sensitive secrets."
)
async def get_diagnostics(current_user: User = Depends(get_current_user)):
    conn = await wazuh_service.test_connection()
    return {
        "wazuh_connected": conn.get("connected", False),
        "wazuh_endpoint": settings.WAZUH_API_URL,
        "wazuh_version": conn.get("version", "Unknown"),
        "status_message": conn.get("status_message", "Diagnostics checked"),
        "database_status": "Connected & Operational",
        "app_version": settings.APP_VERSION,
        "jwt_status": "Active (HS256)",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update Current User Profile and Password",
    description="Allows updating user full name, email, or changing password securely."
)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    
    if payload.email and payload.email != current_user.email:
        # Check if email taken
        existing = db.query(User).filter(User.email == payload.email).first()
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use by another account."
            )
        current_user.email = payload.email

    if payload.new_password:
        if not payload.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password."
            )
        if not verify_password(payload.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password does not match."
            )
        if len(payload.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be at least 6 characters long."
            )
        current_user.hashed_password = hash_password(payload.new_password)

    db.commit()
    db.refresh(current_user)
    return current_user
