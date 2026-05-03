from typing import List, Dict, Any, Optional
from app.schemas import ReminderCreate, ReminderUpdate
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool
from datetime import datetime

from datetime import datetime, timedelta
from app.services.unified_reminder_service import process_unified_reminder
from app.schemas.unified_reminder import UnifiedReminderRequest

async def process_upcoming_reminders() -> Dict[str, Any]:
    """
    Find reminders scheduled for the next 2 days and send notifications.
    """
    today = datetime.utcnow().date()
    two_days_later = today + timedelta(days=2)
    
    # Fetch reminders in range that are still 'pending'
    result = await run_in_threadpool(
        lambda: supabase.table("reminders")
        .select("*, patients(*)")
        .gte("scheduled_date", today.isoformat())
        .lte("scheduled_date", two_days_later.isoformat())
        .eq("sent_status", "pending")
        .execute()
    )
    
    reminders = result.data if result.data else []
    processed_count = 0
    success_count = 0
    
    for reminder in reminders:
        patient = reminder.get("patients")
        if not patient or not patient.get("phone_number") or not patient.get("email"):
            continue
            
        # Prepare message
        if reminder.get("reminder_type") == "doctor_visit":
            doctor_info = f" with Dr. {reminder['doctor_name']}" if reminder.get("doctor_name") else ""
            message = f"Reminder: You have a doctor visit appointment{doctor_info} on {reminder['scheduled_date']}. - Burjeel Smart Care"
        else:
            message = f"Reminder: Please take your medication '{reminder['medication_name']}' on {reminder['scheduled_date']}. - Burjeel Smart Care"
            
        # Create unified request
        request = UnifiedReminderRequest(
            phone_number=patient["phone_number"],
            email_address=patient["email"],
            message_content=message,
            subject="Appointment Reminder - Burjeel Smart Care"
        )
        
        # Send notifications
        response = await process_unified_reminder(request)
        
        # Update reminder status
        sent_status = "sent" if response.overall_success else "failed"
        delivery_confirmation = "delivered" if response.overall_success else "failed"
        
        await run_in_threadpool(
            lambda: supabase.table("reminders")
            .update({
                "sent_status": sent_status,
                "delivery_confirmation": delivery_confirmation,
                "updated_at": datetime.utcnow().isoformat()
            })
            .eq("reminder_id", reminder["reminder_id"])
            .execute()
        )
        
        processed_count += 1
        if response.overall_success:
            success_count += 1
            
    return {
        "total_found": len(reminders),
        "processed": processed_count,
        "successful": success_count
    }

async def create_reminder(
    reminder_in: ReminderCreate,
    created_by: Optional[int] = None
) -> Dict[str, Any]:
    reminder_data = reminder_in.model_dump()
    reminder_data["scheduled_date"] = reminder_data["scheduled_date"].isoformat()
    reminder_data["created_by"] = created_by
    reminder_data["created_at"] = datetime.utcnow().isoformat()
    reminder_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = await run_in_threadpool(
        lambda: supabase.table("reminders").insert(reminder_data).execute()
    )
    return result.data[0] if result.data else {}

async def get_reminder(reminder_id: int) -> Optional[Dict[str, Any]]:
    result = await run_in_threadpool(
        lambda: supabase.table("reminders").select("*").eq("reminder_id", reminder_id).execute()
    )
    return result.data[0] if result.data else None

async def get_reminders_by_patient(patient_id: int) -> List[Dict[str, Any]]:
    result = await run_in_threadpool(
        lambda: supabase.table("reminders").select("*").eq("patient_id", patient_id).execute()
    )
    return result.data

async def update_reminder(
    reminder_id: int,
    reminder_in: ReminderUpdate
) -> Dict[str, Any]:
    update_data = reminder_in.model_dump(exclude_unset=True)
    if "scheduled_date" in update_data and update_data["scheduled_date"]:
        update_data["scheduled_date"] = update_data["scheduled_date"].isoformat()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = await run_in_threadpool(
        lambda: supabase.table("reminders").update(update_data).eq("reminder_id", reminder_id).execute()
    )
    return result.data[0] if result.data else {}

async def delete_reminder(reminder_id: int) -> None:
    await run_in_threadpool(
        lambda: supabase.table("reminders").delete().eq("reminder_id", reminder_id).execute()
    )
