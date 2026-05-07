from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_active_user, RoleChecker
from app.schemas.user import UserResponse, UserUpdate
from app.services import auth_service, audit_service
from app.core.security import get_password_hash
from app.core.validators import validate_password_complexity
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.put("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    status_update: dict,
    current_user: dict = Depends(RoleChecker(["admin"]))
):
    """Admin: Suspend or activate a user account."""
    new_status = status_update.get("account_status")
    if new_status not in ["active", "suspended", "inactive"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    updated_user = await auth_service.update_user(user_id, {"account_status": new_status})
    return updated_user

from app.schemas.user import UserResponse, UserUpdate, AdminUserUpdate

@router.put("/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: int,
    user_in: AdminUserUpdate,
    current_user: dict = Depends(RoleChecker(["admin"]))
):
    """Admin: Full edit rights to any profile."""
    update_data = user_in.model_dump(exclude_unset=True)
    try:
        updated_user = await auth_service.update_user(user_id, update_data)
        
        await audit_service.log_action(
            user_id=current_user["user_id"],
            action="UPDATE_USER",
            entity_type="user",
            entity_id=user_id,
            details={"updated_fields": list(update_data.keys())}
        )
        return updated_user
    except Exception as e:
        logger.error(f"System Error: Admin {current_user['user_id']} failed to update user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="System Error: Failed to update user profile.")

@router.delete("/{user_id}")
async def admin_delete_user(
    user_id: int,
    current_user: dict = Depends(RoleChecker(["admin"]))
):
    """Admin: Delete a user profile."""
    try:
        # Delete user - cascading should delete from patients/doctors if configured in DB,
        # otherwise we manually delete from users and rely on auth_service handling or cascading.
        from app.core.supabase import supabase
        from fastapi.concurrency import run_in_threadpool
        await run_in_threadpool(lambda: supabase.table("users").delete().eq("user_id", user_id).execute())
        
        await audit_service.log_action(
            user_id=current_user["user_id"],
            action="DELETE_USER",
            entity_type="user",
            entity_id=user_id,
            details={"reason": "Admin initiated user deletion"}
        )
        logger.info(f"Admin {current_user['user_id']} successfully deleted user {user_id}.")
        return {"message": "User deleted successfully."}
    except Exception as e:
        logger.error(f"System Error: Admin {current_user['user_id']} failed to delete user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="System Error: Failed to delete user.")

@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    password_data: dict,
    current_user: dict = Depends(RoleChecker(["admin"]))
):
    """Admin: Reset a user's password."""
    new_password = password_data.get("new_password")
    
    if not new_password:
        logger.warning(f"Validation Error: Admin {current_user['user_id']} attempted to reset password for user {user_id} without providing new_password.")
        raise HTTPException(status_code=400, detail="Validation Error: new_password must be provided.")
        
    try:
        # Validate password complexity
        validate_password_complexity(new_password)
    except HTTPException as e:
        logger.warning(f"Validation Error: Admin {current_user['user_id']} password reset for user {user_id} failed complexity check: {e.detail}")
        raise e

    try:
        hashed = get_password_hash(new_password)
        await auth_service.update_user(user_id, {"password_hash": hashed})
        
        await audit_service.log_action(
            user_id=current_user["user_id"],
            action="RESET_PASSWORD",
            entity_type="user",
            entity_id=user_id,
            details={"reason": "Admin initiated password reset"}
        )
        logger.info(f"Admin {current_user['user_id']} successfully reset password for user {user_id}.")
        return {"message": "Password reset successfully."}
    except Exception as e:
        logger.error(f"System Error: Admin {current_user['user_id']} failed to reset password for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="System Error: An unexpected error occurred while resetting the password.")

@router.get("/audit-logs")
async def get_system_audit_logs(
    current_user: dict = Depends(RoleChecker(["admin"])),
    limit: int = 100
):
    """Admin: View system audit logs."""
    return await audit_service.get_audit_logs(limit)
