from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas import PatientCreate, PatientUpdate, PatientResponse, UserCreate
from app.services import auth_service
from app.services.supabase_service import supabase_service
from app.api.deps import get_current_active_user, RoleChecker
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_in: PatientCreate,
    current_user: dict = Depends(RoleChecker(["admin", "doctor"]))
):
    existing_user = await auth_service.get_user_by_username(patient_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    user_in = UserCreate(
        username=patient_in.username,
        email=patient_in.email,
        password=patient_in.password,
        role="patient"
    )
    user = await auth_service.create_user(user_in, created_by=current_user["user_id"])
    
    patient_data = {
        "user_id": user["user_id"],
        "full_name": patient_in.full_name,
        "phone_number": patient_in.phone_number,
        "medical_record_ref": patient_in.medical_record_ref,
        "registered_date": patient_in.registered_date.isoformat(),
        "created_by": current_user["user_id"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    return await supabase_service.create_patient(patient_data)


@router.get("/me", response_model=PatientResponse)
async def get_current_patient(
    current_user: dict = Depends(RoleChecker(["patient"]))
):
    from app.core.supabase import supabase
    from fastapi.concurrency import run_in_threadpool
    
    result = await run_in_threadpool(
        lambda: supabase.table("patients").select("*, users!patients_user_id_fkey(username, email, gender, profile_picture_url)").eq("user_id", current_user["user_id"]).execute()
    )
    
    data = result.data if result.data else []
    if not data:
        raise HTTPException(status_code=404, detail="Patient profile not found")
        
    patient = data[0]
    if "users" in patient and patient["users"]:
        user_info = patient["users"][0] if isinstance(patient["users"], list) else patient["users"]
        patient["username"] = user_info.get("username")
        patient["email"] = user_info.get("email")
        patient["gender"] = user_info.get("gender")
        patient["profile_picture_url"] = user_info.get("profile_picture_url")
        del patient["users"]
        
    return patient

@router.get("/", response_model=List[PatientResponse])
async def get_patients(
    name: Optional[str] = None,
    current_user: dict = Depends(RoleChecker(["admin", "doctor"]))
):
    return await supabase_service.get_patients(name)


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient_in: PatientUpdate,
    current_user: dict = Depends(RoleChecker(["admin", "doctor"]))
):
    from app.core.supabase import supabase
    from fastapi.concurrency import run_in_threadpool
    
    result = await run_in_threadpool(
        lambda: supabase.table("patients").select("*").eq("patient_id", patient_id).execute()
    )
    patient = result.data[0] if result.data else None
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    update_data = patient_in.model_dump(exclude_unset=True)
    if "registered_date" in update_data and update_data["registered_date"]:
        update_data["registered_date"] = update_data["registered_date"].isoformat()
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = await run_in_threadpool(
        lambda: supabase.table("patients").update(update_data).eq("patient_id", patient_id).execute()
    )
    return result.data[0] if result.data else {}

@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: int,
    current_user: dict = Depends(RoleChecker(["admin"]))
):
    from app.core.supabase import supabase
    from fastapi.concurrency import run_in_threadpool
    
    # First get the user_id so we can delete the core user account too if needed
    result = await run_in_threadpool(
        lambda: supabase.table("patients").select("*").eq("patient_id", patient_id).execute()
    )
    patient = result.data[0] if result.data else None
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    # Delete the user account which will cascade to patient if configured, 
    # but we'll do both to be safe
    await run_in_threadpool(
        lambda: supabase.table("users").delete().eq("user_id", patient["user_id"]).execute()
    )
    
    return {"message": "Patient deleted successfully"}
