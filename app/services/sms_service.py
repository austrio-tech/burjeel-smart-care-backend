from typing import Optional, Dict, Any, Tuple
from app.core.config import settings
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool
from datetime import datetime

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


async def send_sms(
    reminder: Dict[str, Any],
    patient: Dict[str, Any],
    created_by: Optional[int] = None
) -> Tuple[bool, str]:
    if not TWILIO_AVAILABLE or not settings.TWILIO_ACCOUNT_SID:
        gateway_response = "Twilio not configured"
        sms_log_data = {
            "reminder_id": reminder["reminder_id"],
            "gateway_response": gateway_response,
            "created_by": created_by,
            "sent_timestamp": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        await run_in_threadpool(lambda: supabase.table("sms_log").insert(sms_log_data).execute())
        
        await run_in_threadpool(
            lambda: supabase.table("reminders").update({
                "sent_status": "failed",
                "delivery_confirmation": "failed",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("reminder_id", reminder["reminder_id"]).execute()
        )
        return False, gateway_response

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    if reminder.get("reminder_type") == "doctor_visit":
        doctor_info = f" with Dr. {reminder['doctor_name']}" if reminder.get("doctor_name") else ""
        message_body = f"Reminder: You have a doctor visit appointment{doctor_info} on {reminder['scheduled_date']}. - Burjeel Smart Care"
    else:
        message_body = f"Reminder: Please take your medication '{reminder['medication_name']}' on {reminder['scheduled_date']}. - Burjeel Smart Care"
    
    sent_status = "failed"
    delivery_confirmation = "failed"
    
    try:
        message = client.messages.create(
            body=message_body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=patient["phone_number"]
        )
        gateway_response = f"Message SID: {message.sid}"
        sent_status = "sent"
        delivery_confirmation = "delivered"
    except Exception as e:
        gateway_response = str(e)

    sms_log_data = {
        "reminder_id": reminder["reminder_id"],
        "gateway_response": gateway_response,
        "created_by": created_by,
        "sent_timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    await run_in_threadpool(lambda: supabase.table("sms_log").insert(sms_log_data).execute())
    
    await run_in_threadpool(
        lambda: supabase.table("reminders").update({
            "sent_status": sent_status,
            "delivery_confirmation": delivery_confirmation,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("reminder_id", reminder["reminder_id"]).execute()
    )
    
    return sent_status == "sent", gateway_response
