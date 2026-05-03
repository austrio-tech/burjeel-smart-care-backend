from datetime import datetime
from typing import Optional, Dict, Any
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

async def create_user(user_in: UserCreate, created_by: Optional[int] = None) -> Dict[str, Any]:
    hashed_password = get_password_hash(user_in.password)
    user_data = {
        "username": user_in.username,
        "email": user_in.email,
        "password_hash": hashed_password,
        "role": user_in.role,
        "created_by": created_by,
        "account_status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    return await supabase_service.create_user(user_data)

async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    return await supabase_service.get_user_by_username(username)

async def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    result = await run_in_threadpool(
        lambda: supabase.table("users").select("*").eq("user_id", user_id).execute()
    )
    return result.data[0] if result.data else None

async def update_user(user_id: int, user_in: UserUpdate) -> Dict[str, Any]:
    update_data = user_in.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow().isoformat()
    
    result = await run_in_threadpool(
        lambda: supabase.table("users").update(update_data).eq("user_id", user_id).execute()
    )
    return result.data[0] if result.data else {}
