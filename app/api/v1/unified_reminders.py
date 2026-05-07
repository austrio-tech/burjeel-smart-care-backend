from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas.unified_reminder import UnifiedReminderRequest, UnifiedReminderResponse
from app.services import unified_reminder_service
from app.api.deps import get_current_active_user, RoleChecker
from datetime import datetime, timedelta
from typing import Dict, Tuple

router = APIRouter()

# Simple in-memory rate limiter: {user_id: [timestamps]}
rate_limit_store: Dict[int, list] = {}
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 5

def check_rate_limit(user_id: int):
    now = datetime.utcnow()
    if user_id not in rate_limit_store:
        rate_limit_store[user_id] = []
    
    # Clean up old timestamps
    rate_limit_store[user_id] = [
        ts for ts in rate_limit_store[user_id] 
        if now - ts < timedelta(seconds=RATE_LIMIT_WINDOW)
    ]
    
    if len(rate_limit_store[user_id]) >= MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
    
    rate_limit_store[user_id].append(now)

@router.post("/", response_model=UnifiedReminderResponse)
async def send_unified_reminder(
    request: UnifiedReminderRequest,
    current_user: dict = Depends(RoleChecker(["admin", "doctor", "pharmacist", "it_staff"]))
):
    """
    Send a unified reminder via both SMS (Twilio) and Email (Gmail).
    Requires admin, pharmacist, or it_staff role.
    Includes rate limiting and retry logic.
    """
    # Apply rate limiting
    check_rate_limit(current_user["user_id"])
    
    # Input sanitization (Pydantic handles most of it, but we can add more if needed)
    # request.message_content = request.message_content.strip()
    
    try:
        response = await unified_reminder_service.process_unified_reminder(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the reminder: {str(e)}"
        )
