from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from app.schemas import ReminderCreate, ReminderUpdate, ReminderResponse
from app.services import reminder_service, sms_service
from app.api.deps import get_current_active_user, RoleChecker
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool

router = APIRouter()


@router.post("/", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
async def create_reminder(
    reminder_in: ReminderCreate,
    current_user: dict = Depends(RoleChecker(["admin", "pharmacist"]))
):
    patient_result = await run_in_threadpool(
        lambda: supabase.table("patients").select("*").eq("patient_id", reminder_in.patient_id).execute()
    )
    if not patient_result.data:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    reminder = await reminder_service.create_reminder(
        reminder_in, created_by=current_user["user_id"]
    )
    return reminder


@router.get("/", response_model=List[ReminderResponse])
async def get_reminders(
    patient_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user)
):
    if patient_id:
        return await reminder_service.get_reminders_by_patient(patient_id)
    else:
        result = await run_in_threadpool(
            lambda: supabase.table("reminders").select("*").execute()
        )
        return result.data


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
    current_user: dict = Depends(RoleChecker(["admin", "pharmacist"]))
):
    reminder = await reminder_service.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    return await reminder_service.update_reminder(reminder_id, reminder_in)


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reminder(
    reminder_id: int,
    current_user: dict = Depends(RoleChecker(["admin", "pharmacist"]))
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
    current_user: dict = Depends(RoleChecker(["admin", "pharmacist"]))
):
    reminder = await reminder_service.get_reminder(reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    patient_result = await run_in_threadpool(
        lambda: supabase.table("patients").select("*").eq("patient_id", reminder["patient_id"]).execute()
    )
    patient = patient_result.data[0] if patient_result.data else None
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Note: sms_service also needs to be updated to use Supabase
    success, response = await sms_service.send_sms(
        reminder, patient, created_by=current_user["user_id"]
    )
    return {"success": success, "response": response}
