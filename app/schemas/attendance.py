from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel


class AttendanceBase(BaseModel):
    reminder_id: Optional[int] = None
    patient_id: int
    appointment_date: date
    status: str


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    status: Optional[str] = None


class AttendanceResponse(AttendanceBase):
    attendance_id: int
    marked_by: int
    timestamp: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
