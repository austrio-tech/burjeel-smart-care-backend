from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class ReminderBase(BaseModel):
    patient_id: int
    display_name: Optional[str] = None
    scheduled_date: datetime
    reminder_type: str = "medication"  # medication or doctor_visit


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    display_name: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    reminder_type: Optional[str] = None
    success_sent: Optional[int] = None
    failed_sent: Optional[int] = None


class ReminderResponse(ReminderBase):
    reminder_id: int
    success_sent: int = 0
    failed_sent: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
