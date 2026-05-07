from datetime import datetime
from typing import List, Optional, Dict, Any
from app.core.security import verify_password, get_password_hash
from app.schemas import UserCreate, UserUpdate
from app.services.supabase_service import supabase_service
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool

async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    user = await supabase_service.get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.get("password_hash")):
        return None
    
    # Update last login
    await run_in_threadpool(
        lambda: supabase.table("users").update({"last_login": datetime.utcnow().isoformat()}).eq("user_id", user["user_id"]).execute()
    )
    
    return user

async def create_user(user_in: Any, created_by: Optional[int] = None) -> Dict[str, Any]:
    hashed_password = get_password_hash(user_in.password)
    user_data = {
        "username": user_in.username,
        "email": user_in.email,
        "password_hash": hashed_password,
        "role": user_in.role,
        "gender": getattr(user_in, "gender", None),
        "created_by": created_by,
        "account_status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    created_user = await supabase_service.create_user(user_data)
    
    if not created_user:
        return {}

    user_id = created_user.get("user_id")

    try:
        if user_in.role == "doctor":
            doctor_data = {
                "user_id": user_id,
                "specialty": getattr(user_in, "specialty", None),
                "license_number": getattr(user_in, "license_number", None),
                "department": getattr(user_in, "department", None),
                "created_at": datetime.utcnow().isoformat()
            }
            await run_in_threadpool(lambda: supabase.table("doctors").insert(doctor_data).execute())
        
        elif user_in.role == "patient" and getattr(user_in, "full_name", None):
            patient_data = {
                "user_id": user_id,
                "full_name": getattr(user_in, "full_name"),
                "phone_number": getattr(user_in, "phone_number", None),
                "medical_record_ref": getattr(user_in, "medical_record_ref", None),
                "registered_date": getattr(user_in, "registered_date", datetime.utcnow().isoformat().split('T')[0])
            }
            await run_in_threadpool(lambda: supabase.table("patients").insert(patient_data).execute())
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to create specific record for user {user_id}. Rolling back. Error: {str(e)}")
        await run_in_threadpool(lambda: supabase.table("users").delete().eq("user_id", user_id).execute())
        raise ValueError(f"Failed to create {user_in.role} record due to system or database constraint error.")

    return created_user

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    return await supabase_service.get_user_by_username(username)

async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    result = await run_in_threadpool(
        lambda: supabase.table("users").select("*").eq("user_id", user_id).execute()
    )
    return result.data[0] if result.data else None

async def get_users_by_role(role: str) -> List[Dict[str, Any]]:
    if role == "doctor":
        # Fetch related doctor details using specific foreign key
        result = await run_in_threadpool(
            lambda: supabase.table("users").select("*, doctors!doctors_user_id_fkey(specialty, department, license_number)").eq("role", role).execute()
        )
        data = result.data if result.data else []
        for user in data:
            if "doctors" in user and user["doctors"]:
                doctor_info = user["doctors"][0] if isinstance(user["doctors"], list) else user["doctors"]
                user["specialty"] = doctor_info.get("specialty")
                user["department"] = doctor_info.get("department")
                user["license_number"] = doctor_info.get("license_number")
                del user["doctors"]
        return data
    else:
        result = await run_in_threadpool(
            lambda: supabase.table("users").select("*").eq("role", role).execute()
        )
        return result.data if result.data else []

async def get_all_users() -> List[Dict[str, Any]]:
    result = await run_in_threadpool(
        lambda: supabase.table("users").select("*").execute()
    )
    return result.data if result.data else []

async def update_user(user_id: int, user_in: Dict[str, Any] | UserUpdate) -> Dict[str, Any]:
    if hasattr(user_in, "model_dump"):
        update_data = user_in.model_dump(exclude_unset=True)
    else:
        update_data = dict(user_in)
    
    # Extract doctor/patient specific fields before updating users table
    doctor_fields = ["specialty", "department", "license_number"]
    doctor_update = {k: update_data.pop(k) for k in doctor_fields if k in update_data}
    
    patient_fields = ["full_name", "phone_number", "medical_record_ref", "registered_date"]
    patient_update = {k: update_data.pop(k) for k in patient_fields if k in update_data}

    if update_data:
        update_data["updated_at"] = datetime.utcnow().isoformat()
        result = await run_in_threadpool(
            lambda: supabase.table("users").update(update_data).eq("user_id", user_id).execute()
        )
        updated_user = result.data[0] if result.data else {}
    else:
        # If there are only role specific fields
        updated_user = {}

    if doctor_update:
        await run_in_threadpool(lambda: supabase.table("doctors").update(doctor_update).eq("user_id", user_id).execute())
        
    # We won't update patients table here since there is a dedicated patient update endpoint or 
    # if it's admin update, we can update it too:
    if patient_update:
        # Check if patient exists, if so update it
        try:
            await run_in_threadpool(lambda: supabase.table("patients").update(patient_update).eq("user_id", user_id).execute())
        except Exception:
            pass # ignore if not a patient
            
    return updated_user

