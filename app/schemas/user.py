from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str
    gender: Optional[str] = None
    profile_picture_url: Optional[str] = None


class UserCreate(UserBase):
    password: str

class AdminUserCreate(UserCreate):
    specialty: Optional[str] = None
    license_number: Optional[str] = None
    department: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    medical_record_ref: Optional[str] = None
    registered_date: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    account_status: Optional[str] = None
    gender: Optional[str] = None
    profile_picture_url: Optional[str] = None
    notification_preferences: Optional[dict] = None

class AdminUserUpdate(UserUpdate):
    specialty: Optional[str] = None
    department: Optional[str] = None
    license_number: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    medical_record_ref: Optional[str] = None
    registered_date: Optional[str] = None


class UserResponse(UserBase):
    user_id: int
    last_login: Optional[datetime] = None
    account_status: str
    notification_preferences: Optional[dict] = None
    two_factor_enabled: Optional[bool] = False
    created_at: datetime
    updated_at: datetime
    
    # Doctor/Patient specific optional fields
    specialty: Optional[str] = None
    department: Optional[str] = None
    license_number: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
