from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from app.models.user import User
from app.schemas.user import HomeResponse, UserResponse
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/home", tags=["Home / Dashboard"])


@router.get(
    "/me",
    response_model=HomeResponse,
    summary="Protected Home User Profile (API 3)",
    description="Returns current authenticated user details and home feed status. Requires valid JWT Bearer token."
)
def get_home_user_data(current_user: User = Depends(get_current_user)):
    return {
        "message": f"مرحباً بك {current_user.full_name or current_user.username} في الصفحة الرئيسية!",
        "user": current_user,
        "status": "authenticated",
        "server_time": datetime.now(timezone.utc)
    }
