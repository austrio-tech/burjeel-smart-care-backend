from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import get_current_active_user
from app.schemas.user import UserResponse, UserUpdate
from app.services import auth_service
from app.core.validators import validate_password_complexity
from app.core.security import get_password_hash, verify_password

router = APIRouter()

@router.put("/", response_model=UserResponse)
async def update_profile(
    user_in: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """Universal: Update own profile details."""
    update_data = user_in.model_dump(exclude_unset=True)
    # Prevent users from updating their own role, account_status, or user_id
    for key in ["role", "account_status", "user_id"]:
        update_data.pop(key, None)
        
    updated_user = await auth_service.update_user(current_user["user_id"], update_data)
    return updated_user

import logging
logger = logging.getLogger(__name__)

@router.put("/password")
async def update_password(
    password_data: dict,
    current_user: dict = Depends(get_current_active_user)
):
    """Universal: Change own password."""
    old_password = password_data.get("old_password")
    new_password = password_data.get("new_password")
    
    if not old_password or not new_password:
        logger.warning(f"Password update failed for user {current_user['username']}: Missing old or new password.")
        raise HTTPException(status_code=400, detail="Must provide both old_password and new_password.")
        
    try:
        user_with_hash = await auth_service.get_user_by_username(current_user["username"])
        if not user_with_hash or "password_hash" not in user_with_hash:
            logger.error(f"System Error: User {current_user['username']} not found or missing password hash.")
            raise HTTPException(status_code=500, detail="System Error: Could not verify current user credentials.")
            
        if not verify_password(old_password, user_with_hash["password_hash"]):
            logger.warning(f"Validation Error: Incorrect current password provided for user {current_user['username']}.")
            raise HTTPException(status_code=400, detail="Validation Error: Incorrect current password.")
            
        # This raises HTTPException(400) directly if it fails
        try:
            validate_password_complexity(new_password)
        except HTTPException as e:
            logger.warning(f"Validation Error: Password complexity failed for user {current_user['username']} - {e.detail}")
            raise e
        
        hashed = get_password_hash(new_password)
        await auth_service.update_user(current_user["user_id"], {"password_hash": hashed})
        logger.info(f"User {current_user['username']} successfully updated their password.")
        
        return {"message": "Password updated successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"System Error during password update for user {current_user['username']}: {str(e)}")
        raise HTTPException(status_code=500, detail="System Error: An unexpected error occurred while updating the password.")

from fastapi import UploadFile, File
import time
import os

@router.post("/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    """Universal: Upload profile picture."""
    from app.core.supabase import supabase
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")
        
    try:
        file_bytes = await file.read()
        file_extension = os.path.splitext(file.filename)[1]
        file_path = f"{current_user['user_id']}_avatar_{int(time.time())}{file_extension}"
        
        # Upload to Supabase Storage
        result = supabase.storage.from_("avatars").upload(
            file_path, 
            file_bytes, 
            {"content-type": file.content_type}
        )
        
        # Get public URL
        public_url = supabase.storage.from_("avatars").get_public_url(file_path)
        
        # Update user profile_picture_url
        updated_user = await auth_service.update_user(current_user["user_id"], {"profile_picture_url": public_url})
        return updated_user
    except Exception as e:
        logger.error(f"Error uploading avatar for user {current_user['user_id']}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")
