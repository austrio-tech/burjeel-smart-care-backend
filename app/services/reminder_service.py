from typing import List, Dict, Any, Optional
from app.schemas import ReminderCreate, ReminderUpdate
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timedelta
import pytz

from app.services.unified_reminder_service import process_unified_reminder
from app.schemas.unified_reminder import UnifiedReminderRequest

import logging
import os

# Configure logging
logger = logging.getLogger(__name__)

MUSCAT_TZ = pytz.timezone("Asia/Muscat")

def format_muscat_time(dt_str: str) -> str:
    """
    Convert UTC datetime string to Asia/Muscat and format as '2:30 PM'.
    """
    try:
        # Parse the ISO string
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        
        # Ensure it's UTC if no timezone info
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
            
        # Convert to Muscat
        muscat_dt = dt.astimezone(MUSCAT_TZ)
        
        # Format as '2:30 PM'
        return muscat_dt.strftime("%I:%M %p")
    except Exception as e:
        logger.error(f"Error formatting Muscat time: {str(e)}")
        return dt_str

def format_muscat_date(dt_str: str) -> str:
    """
    Convert UTC datetime string to Asia/Muscat and format as 'May 04, 2026'.
    """
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        muscat_dt = dt.astimezone(MUSCAT_TZ)
        return muscat_dt.strftime("%B %d, %Y")
    except Exception as e:
        logger.error(f"Error formatting Muscat date: {str(e)}")
        return dt_str

def get_template(template_name: str, ext: str = "html", **kwargs) -> str:
    """
    Load, populate, and return content from the template file.
    """
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Send_Body")
    template_path = os.path.join(template_dir, f"{template_name}.{ext}")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"
            logger.debug(f"Attempting to replace {placeholder} with {value}")
            content = content.replace(placeholder, str(value))
        return content
    except Exception as e:
        logger.error(f"Failed to load template {template_name}.{ext}: {str(e)}")
        # Fallback or re-raise
        return f"Content: {str(kwargs)}"


async def _process_reminders(start_dt: datetime, end_dt: datetime) -> Dict[str, Any]:
    """
    Find reminders scheduled between start_dt and end_dt and send notifications.
    """
    logger.info(f"Processing reminders from {start_dt} to {end_dt}")
    
    # Fetch reminders in range that haven't been successfully sent yet
    # Join patients and their associated user to get the email
    result = await run_in_threadpool(
        lambda: supabase.table("reminders")
        .select("*, patients(*, users!patients_user_id_fkey(*))")
        .gte("scheduled_date", start_dt.isoformat())
        .lte("scheduled_date", end_dt.isoformat())
        .eq("success_sent", 0)
        .execute()
    )
    
    reminders = result.data if result.data else []
    logger.info(f"Found {len(reminders)} pending reminders")
    
    processed_count = 0
    success_count = 0
    
    for reminder in reminders:
        reminder_id = reminder.get("reminder_id")
        # Handle potential list or dict for joined data
        patient_data = reminder.get("patients")
        if isinstance(patient_data, list):
            patient = patient_data[0] if patient_data else None
        else:
            patient = patient_data
            
        if not patient:
            logger.warning(f"Reminder {reminder_id} has no associated patient data")
            continue
            
        # Email is stored in the users table, linked to the patient
        # Handle the explicit relationship key name from Supabase
        user_data = patient.get("users!patients_user_id_fkey") or patient.get("users")
        if isinstance(user_data, list):
            user = user_data[0] if user_data else None
        else:
            user = user_data
            
        email = user.get("email") if user else None
        phone = patient.get("phone_number")
        
        if not phone or not email:
            logger.warning(f"Reminder {reminder_id} skipped: missing phone ({phone}) or email ({email})")
            continue
            
        logger.debug(f"Processing reminder {reminder_id} for patient {patient.get('patient_id')}")
        
        # Prepare message
        reminder_type = reminder.get("reminder_type", "medication")
        
        # Determine the name to display (either medication name or doctor name)
        # Using 'display_name' column as a generic 'name' field in DB
        display_name = reminder.get("display_name", "item")
        
        # Format date and time for Muscat
        scheduled_dt_str = str(reminder['scheduled_date'])
        formatted_time = format_muscat_time(scheduled_dt_str)
        formatted_date = format_muscat_date(scheduled_dt_str)
        
        if reminder_type == "doctor_visit":
            details = f"Doctor visit appointment with Dr. {display_name}"
            # message = f"Reminder: You have a doctor visit appointment with Dr. {display_name} on {formatted_date} at {formatted_time}. - Burjeel Smart Care"
        else:
            details = f"Please take your medication '{display_name}'"
            # message = f"Reminder: Please take your medication '{display_name}' on {formatted_date} at {formatted_time}. - Burjeel Smart Care"
            
        # Generate HTML email content and SMS text content
        template_name = "appointment" if reminder_type == "doctor_visit" else "medication"
        subject = "Appointment Reminder - Burjeel Smart Care" if reminder_type == "doctor_visit" else "Medication Reminder - Burjeel Smart Care"
        
        email_html = get_template(
            template_name,
            ext="html",
            patient_name=patient.get("full_name", "Patient"),
            doctor_name=display_name if reminder_type == "doctor_visit" else "Doctor",
            medication_name=display_name,
            scheduled_date=formatted_date,
            time=formatted_time,
            reminder_type=reminder_type.replace("_", " ").title(),
            reminder_details=details
        )
        
        sms_text = get_template(
            template_name,
            ext="txt",
            patient_name=patient.get("full_name", "Patient"),
            doctor_name=display_name if reminder_type == "doctor_visit" else "Doctor",
            medication_name=display_name,
            scheduled_date=formatted_date,
            time=formatted_time,
            reminder_type=reminder_type.replace("_", " ").title(),
            reminder_details=details
        )

        # Create unified request
        try:
            request = UnifiedReminderRequest(
                phone_number=phone,
                email_address=email,
                message_content=sms_text,
                email_content=email_html,
                subject=subject
            )
        except Exception as e:
            logger.error(f"Validation failed for reminder {reminder_id}: {str(e)}")
            continue
        
        # Send notifications
        response = await process_unified_reminder(request)
        
        # Update reminder status
        current_success = reminder.get("success_sent") or 0
        current_failed = reminder.get("failed_sent") or 0
        
        if response.overall_success:
            current_success += 1
        else:
            current_failed += 1
        
        logger.info(f"Reminder {reminder_id} result: SMS={response.sms_status.success}, Email={response.email_status.success}")
        
        await run_in_threadpool(
            lambda: supabase.table("reminders")
            .update({
                "success_sent": current_success,
                "failed_sent": current_failed,
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

async def process_today_reminders() -> Dict[str, Any]:
    """
    Find reminders scheduled for today from now and send notifications.
    """
    now = datetime.utcnow()
    # End of today
    end_of_today = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return await _process_reminders(now, end_of_today)

async def process_upcoming_reminders() -> Dict[str, Any]:
    """
    Find reminders scheduled for the next 2 days from now and send notifications.
    """
    now = datetime.utcnow()
    two_days_later = now + timedelta(days=2)
    return await _process_reminders(now, two_days_later)

async def send_issue_notification(reminder: dict, patient: dict, user: dict):
    if not patient or not user or not user.get("email"):
        return
        
    reminder_type = reminder.get("reminder_type", "medication")
    display_name = reminder.get("display_name", "item")
    phone = patient.get("phone_number")
    email = user.get("email")
    
    # Format date and time for Muscat
    scheduled_dt_str = str(reminder['scheduled_date'])
    formatted_time = format_muscat_time(scheduled_dt_str)
    formatted_date = format_muscat_date(scheduled_dt_str)
    
    if reminder_type == "doctor_visit":
        details = f"Doctor visit appointment with Dr. {display_name}"
        template_name = "appointment_issued"
        subject = "Appointment Created Successfully - Burjeel Smart Care"
    else:
        details = f"Medication '{display_name}' has been issued"
        template_name = "medication_issued"
        subject = "Medication Issued Successfully - Burjeel Smart Care"
        
    email_html = get_template(
        template_name,
        ext="html",
        patient_name=patient.get("full_name", "Patient"),
        doctor_name=display_name if reminder_type == "doctor_visit" else "Doctor",
        medication_name=display_name,
        scheduled_date=formatted_date,
        time=formatted_time,
        reminder_type=reminder_type.replace("_", " ").title(),
        reminder_details=details
    )
    
    sms_text = get_template(
        template_name,
        ext="txt",
        patient_name=patient.get("full_name", "Patient"),
        doctor_name=display_name if reminder_type == "doctor_visit" else "Doctor",
        medication_name=display_name,
        scheduled_date=formatted_date,
        time=formatted_time,
        reminder_type=reminder_type.replace("_", " ").title(),
        reminder_details=details
    )
    
    try:
        request = UnifiedReminderRequest(
            phone_number=phone,
            email_address=email,
            message_content=sms_text,
            email_content=email_html,
            subject=subject
        )
        await process_unified_reminder(request)
    except Exception as e:
        logger.error(f"Failed to send issue notification for reminder {reminder.get('reminder_id')}: {str(e)}")

async def create_reminder(
    reminder_in: ReminderCreate,
    created_by: Optional[int] = None
) -> Dict[str, Any]:
    reminder_data = reminder_in.model_dump()
    reminder_data["scheduled_date"] = reminder_data["scheduled_date"].isoformat()
    reminder_data["created_by"] = created_by
    now = datetime.utcnow().isoformat()
    reminder_data["created_at"] = now
    reminder_data["updated_at"] = now
    
    # Remove fields not present in the database 'reminders' table to avoid PGRST204
    # Your schema has: reminder_id, patient_id, display_name, scheduled_date, sent_status, delivery_confirmation, created_at, updated_at, created_by, reminder_type, message_template
    
    # Remove 'message_template' if not needed (it's in the DB but often unused)
    if "message_template" in reminder_data and reminder_data["message_template"] is None:
        del reminder_data["message_template"]
    
    # Ensure reminder_type is correctly set for the DB check constraint
    if "reminder_type" not in reminder_data or not reminder_data["reminder_type"] or reminder_data["reminder_type"] not in ["medication", "doctor_visit"]:
        reminder_data["reminder_type"] = "medication"
    
    result = await run_in_threadpool(
        lambda: supabase.table("reminders").insert(reminder_data).execute()
    )
    db_reminder = result.data[0] if result.data else {}
            
    return db_reminder

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
    
    # Remove fields not present in the database 'reminders' table to avoid PGRST204
    # Your schema has: reminder_id, patient_id, display_name, scheduled_date, sent_status, delivery_confirmation, created_at, updated_at, created_by, reminder_type, message_template
    
    # Remove 'message_template' if not needed (it's in the DB but often unused)
    if "message_template" in update_data and update_data["message_template"] is None:
        del update_data["message_template"]
    
    # Ensure reminder_type is valid if updated
    if "reminder_type" in update_data:
        if not update_data["reminder_type"] or update_data["reminder_type"] not in ["medication", "doctor_visit"]:
            update_data["reminder_type"] = "medication"
    
    result = await run_in_threadpool(
        lambda: supabase.table("reminders").update(update_data).eq("reminder_id", reminder_id).execute()
    )
    return result.data[0] if result.data else {}

async def delete_reminder(reminder_id: int) -> None:
    await run_in_threadpool(
        lambda: supabase.table("reminders").delete().eq("reminder_id", reminder_id).execute()
    )
