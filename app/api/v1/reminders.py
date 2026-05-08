from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from app.schemas import ReminderCreate, ReminderUpdate, ReminderResponse
from app.services import reminder_service, sms_service
from app.api.deps import get_current_active_user, RoleChecker
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    reminder_in: ReminderCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(RoleChecker(["admin", "doctor"]))
):
    patient_result = await run_in_threadpool(
        lambda: supabase.table("patients").select("*").eq("patient_id", reminder_in.patient_id).execute()
    )
    if not patient_result.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    reminder = await reminder_service.create_reminder(
        reminder_in, created_by=current_user["user_id"]
    )
    
    # Trigger notification immediately
    background_tasks.add_task(send_reminder, reminder["reminder_id"], background_tasks, current_user)
    
    return reminder


@router.get("/", response_model=List[ReminderResponse])
async def get_reminders(
    patient_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user)
):
    query = supabase.table("reminders").select("*")
    
    if patient_id:
        query = query.eq("patient_id", patient_id)
        
    if current_user["role"] == "doctor":
        user_id = current_user["user_id"]
        username = current_user["username"]
        query = query.or_(f"created_by.eq.{user_id},and(reminder_type.eq.doctor_visit,display_name.eq.{username})")
    elif current_user["role"] == "patient":
        # Force fetching their own patient_id
        patient_result = await run_in_threadpool(
            lambda: supabase.table("patients").select("patient_id").eq("user_id", current_user["user_id"]).execute()
        )
        if not patient_result.data:
            return [] # No patient record found
        own_patient_id = patient_result.data[0]["patient_id"]
        # Override any requested patient_id with their own
        query = supabase.table("reminders").select("*").eq("patient_id", own_patient_id)
        
    result = await run_in_threadpool(lambda: query.execute())
    return result.data if result.data else []


@router.get("/process-today")
async def process_today_reminders():
    """
    Check for reminders today and send SMS/Email notifications.
    """
    result = await reminder_service.process_today_reminders()
    return result


@router.get("/process-upcoming")
async def process_upcoming_reminders():
    """
    Check for reminders in the next 2 days and send SMS/Email notifications.
    This endpoint is public to allow easy triggering via browser or cron jobs.
    """
    result = await reminder_service.process_upcoming_reminders()
    return result


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    reminder = await reminder_service.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return reminder


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: int,
    reminder_in: ReminderUpdate,
    current_user: dict = Depends(RoleChecker(["admin", "doctor"]))
):
    reminder = await reminder_service.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    return await reminder_service.update_reminder(reminder_id, reminder_in)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    current_user: dict = Depends(RoleChecker(["admin", "doctor"]))
):
    reminder = await reminder_service.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    await reminder_service.delete_reminder(reminder_id)
    return


@router.post("/{reminder_id}/send")
async def send_reminder(
    reminder_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(RoleChecker(["admin", "doctor"]))
):
    reminder = await reminder_service.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    # Fetch patient with joined user to get email
    # Specify the relationship explicitly to avoid ambiguity (PGRST201)
    patient_result = await run_in_threadpool(
        lambda: supabase.table("patients")
        .select("*, users!patients_user_id_fkey(*)")
        .eq("patient_id", reminder["patient_id"])
        .execute()
    )
    
    patient_data = patient_result.data[0] if patient_result.data else None
    if not patient_data:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Extract email from joined user data
    # Handle the explicit relationship key name from Supabase
    user_data = patient_data.get("users!patients_user_id_fkey") or patient_data.get("users")
    if isinstance(user_data, list):
        user = user_data[0] if user_data else None
    else:
        user = user_data
        
    email = user.get("email") if user else None
    phone = patient_data.get("phone_number")
    
    if not phone or not email:
        raise HTTPException(
            status_code=400, 
            detail="Patient missing phone number or email for notification"
        )

    # Prepare message
    reminder_type = reminder.get("reminder_type", "medication")
    
    # Determine the name to display (either medication name or doctor name)
    # Using 'display_name' column as a generic 'name' field in DB
    display_name = reminder.get("display_name", "item")
    
    from app.services.reminder_service import get_template, format_muscat_time, format_muscat_date
    
    # Format date and time for Muscat
    scheduled_dt_str = str(reminder['scheduled_date'])
    formatted_time = format_muscat_time(scheduled_dt_str)
    formatted_date = format_muscat_date(scheduled_dt_str)
    
    # Select template based on reminder_type
    # 'medication' maps to medication.html/txt
    # 'doctor_visit' maps to appointment.html/txt
    # If it's a new booking (triggered on create), we use the _issued version
    is_new = reminder.get("created_at") == reminder.get("updated_at")
    suffix = "_issued" if is_new else ""
    template_name = ("medication" if reminder_type == "medication" else "appointment") + suffix
    
    # Define template context dynamically
    context = {
        "patient_name": patient_data.get("full_name", "Patient"),
        "reminder_type": reminder_type.replace("_", " ").title(),
        "scheduled_date": formatted_date,
        "time": formatted_time,
    }
    
    if reminder_type == "doctor_visit":
        context["doctor_name"] = display_name
        context["reminder_details"] = f"Doctor visit appointment with Dr. {display_name}"
    else:
        context["reminder_details"] = f"Please take your medication '{display_name}'"
        context["medication_name"] = display_name
    
    email_html = get_template(
        template_name,
        ext="html",
        **context
    )
    
    sms_text = get_template(
        template_name,
        ext="txt",
        **context
    )

    # Determine the correct subject based on type and whether it's new
    if reminder_type == "doctor_visit":
        subject = "Appointment Created Successfully - Burjeel Smart Care" if is_new else "Appointment Reminder - Burjeel Smart Care"
    else:
        subject = "Medication Issued Successfully - Burjeel Smart Care" if is_new else "Medication Reminder - Burjeel Smart Care"

    from app.services.unified_reminder_service import process_unified_reminder
    from app.schemas.unified_reminder import UnifiedReminderRequest
    
    request = UnifiedReminderRequest(
        phone_number=phone,
        email_address=email,
        message_content=sms_text,
        email_content=email_html,
        subject=subject
    )
    
    # Send notifications using the unified service
    response = await process_unified_reminder(request)
    
    # Update reminder status based on overall success
    current_success = reminder.get("success_sent") or 0
    current_failed = reminder.get("failed_sent") or 0
    
    if response.overall_success:
        current_success += 1
    else:
        current_failed += 1
    
    await run_in_threadpool(
        lambda: supabase.table("reminders")
        .update({
            "success_sent": current_success,
            "failed_sent": current_failed,
            "updated_at": datetime.utcnow().isoformat()
        })
        .eq("reminder_id", reminder_id)
        .execute()
    )
    
    return {
        "success": response.overall_success,
        "sms": response.sms_status,
        "email": response.email_status
    }
