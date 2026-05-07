from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class PatientBase(BaseModel):
    full_name: str
    phone_number: str
    medical_record_ref: Optional[str] = None
    registered_date: date


class PatientCreate(PatientBase):
    username: str
    email: str
    password: str


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    medical_record_ref: Optional[str] = None
    registered_date: Optional[date] = None


class PatientResponse(PatientBase):
    patient_id: int
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    profile_picture_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
