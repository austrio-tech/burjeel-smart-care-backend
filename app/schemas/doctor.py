from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class DoctorBase(BaseModel):
    specialty: str
    license_number: str
    department: Optional[str] = None

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(BaseModel):
    specialty: Optional[str] = None
    license_number: Optional[str] = None
    department: Optional[str] = None

class DoctorResponse(DoctorBase):
    doctor_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
