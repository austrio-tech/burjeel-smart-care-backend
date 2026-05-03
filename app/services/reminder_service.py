from typing import List, Dict, Any, Optional
from app.schemas import ReminderCreate, ReminderUpdate
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool
from datetime import datetime

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
