import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Tuple
from app.core.config import settings
from app.services.sms_service import send_textbee_sms
from app.core.gmail_service import send_google_email
from app.schemas.unified_reminder import UnifiedReminderRequest, UnifiedReminderResponse, ServiceStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def retry_operation(operation, *args, max_retries=3, delay=1):
    """Simple retry logic for async operations"""
    last_exception = None
    for attempt in range(max_retries):
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args)
            return operation(*args)
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (attempt + 1))
    raise last_exception

async def send_unified_sms(phone_number: str, message: str) -> Tuple[bool, str]:
    success = await send_textbee_sms(phone_number, message)
    if success:
        return True, "SMS sent successfully via TextBee"
    return False, "Failed to send SMS via TextBee"

async def send_unified_email(email: str, subject: str, body: str) -> Tuple[bool, str]:
    try:
        # send_google_email is synchronous (uses requests)
        res = await retry_operation(send_google_email, [email], subject, body)
        if res.get("success"):
            return True, res.get("message", "Email sent successfully")
        return False, res.get("message", "Email failed")
    except Exception as e:
        logger.error(f"Email failed after retries: {str(e)}")
        return False, str(e)

async def process_unified_reminder(request: UnifiedReminderRequest) -> UnifiedReminderResponse:
    # Send both simultaneously
    # Use email_content if provided, otherwise fallback to message_content
    email_body = request.email_content if request.email_content else request.message_content
    
    sms_task = asyncio.create_task(send_unified_sms(request.phone_number, request.message_content))
    email_task = asyncio.create_task(send_unified_email(request.email_address, request.subject, email_body))
    
    sms_success, sms_msg = await sms_task
    email_success, email_msg = await email_task
    
    return UnifiedReminderResponse(
        sms_status=ServiceStatus(success=sms_success, message=sms_msg),
        email_status=ServiceStatus(success=email_success, message=email_msg),
        overall_success=sms_success and email_success
    )
