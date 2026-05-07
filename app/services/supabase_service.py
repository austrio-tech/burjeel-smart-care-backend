from typing import List, Dict, Any, Optional
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool

class SupabaseService:
    @staticmethod
    async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        result = await run_in_threadpool(
            lambda: supabase.table("users").select("*").eq("username", username).execute()
        )
        return result.data[0] if result.data else None

    @staticmethod
    async def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        result = await run_in_threadpool(
            lambda: supabase.table("users").insert(user_data).execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_patients(name: Optional[str] = None) -> List[Dict[str, Any]]:
        # Fetch patient details alongside their associated user details using the exact foreign key
        query = supabase.table("patients").select("*, users!patients_user_id_fkey(username, email, gender, profile_picture_url)")
        if name:
            query = query.ilike("full_name", f"%{name}%")
        
        result = await run_in_threadpool(lambda: query.execute())
        data = result.data if result.data else []
        
        # Flatten the nested users dict into the patient dict for easier frontend consumption
        for patient in data:
            if "users" in patient and patient["users"]:
                user_info = patient["users"][0] if isinstance(patient["users"], list) else patient["users"]
                patient["username"] = user_info.get("username")
                patient["email"] = user_info.get("email")
                patient["gender"] = user_info.get("gender")
                patient["profile_picture_url"] = user_info.get("profile_picture_url")
                del patient["users"]
        
        return data

    @staticmethod
    async def create_patient(patient_data: Dict[str, Any]) -> Dict[str, Any]:
        result = await run_in_threadpool(
            lambda: supabase.table("patients").insert(patient_data).execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_reminders(patient_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = supabase.table("reminders").select("*")
        if patient_id:
            query = query.eq("patient_id", patient_id)
        
        result = await run_in_threadpool(lambda: query.execute())
        return result.data

    @staticmethod
    async def create_reminder(reminder_data: Dict[str, Any]) -> Dict[str, Any]:
        result = await run_in_threadpool(
            lambda: supabase.table("reminders").insert(reminder_data).execute()
        )
        return result.data[0] if result.data else {}

    @staticmethod
    async def get_attendance_report(from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        # This is a simplified version, you might need more complex logic for reports
        query = supabase.table("attendance").select("*")
        if from_date:
            query = query.gte("appointment_date", from_date)
        if to_date:
            query = query.lte("appointment_date", to_date)
        
        result = await run_in_threadpool(lambda: query.execute())
        data = result.data
        
        total = len(data)
        came = len([r for r in data if r.get("status") == "came"])
        rate = (came / total * 100) if total > 0 else 0
        
        return {
            "total_attendances": total,
            "attendance_rate": round(rate, 2),
            "data": data
        }

supabase_service = SupabaseService()
