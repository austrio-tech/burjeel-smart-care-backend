import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

async def send_textbee_sms(phone_number: str, message: str) -> bool:
    """
    Sends SMS using TextBee API.
    """
    if not settings.KEY:
        logger.error("TextBee KEY not configured")
        return False
    
    # TextBee API requires device ID in the URL.
    # The current KEY in settings might be the API key, 
    # but we also need a DEVICE_ID if we are to use the correct endpoint.
    # Based on TextBee documentation, the endpoint is:
    # https://api.textbee.dev/api/v1/gateway/devices/{DEVICE_ID}/send-sms
    
    # As I don't have a DEVICE_ID environment variable, I'll log an error for now
    # or you might need to add DEVICE_ID to settings.
    
    # Assuming you might have the Device ID or it's part of your configuration.
    device_id = settings.DEVICE_ID
    if not device_id:
        logger.error("TextBee DEVICE_ID not configured")
        return False

    url = f"https://api.textbee.dev/api/v1/gateway/devices/{device_id}/send-sms"
    payload = {
        "recipients": [phone_number],
        "message": message
    }
    headers = {
        "x-api-key": settings.KEY,
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                logger.info(f"SMS sent successfully via TextBee to {phone_number}")
                return True
            else:
                logger.error(f"TextBee API error: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send SMS via TextBee: {str(e)}")
        return False
