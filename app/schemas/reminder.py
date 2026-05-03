from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class ReminderBase(BaseModel):
    patient_id: int
    medication_name: str
    scheduled_date: date
    reminder_type: str = "medication"  # medication or doctor_visit
    doctor_name: Optional[str] = None


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    medication_name: Optional[str] = None
    scheduled_date: Optional[date] = None
    reminder_type: Optional[str] = None
    doctor_name: Optional[str] = None
    sent_status: Optional[str] = None
    delivery_confirmation: Optional[str] = None


class ReminderResponse(ReminderBase):
    reminder_id: int
    sent_status: str
    delivery_confirmation: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
