from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.services import report_service
from app.api.deps import get_current_active_user, RoleChecker

router = APIRouter()


@router.get("/attendance/")
async def get_attendance_report(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(RoleChecker(["admin", "doctor", "pharmacist", "it_staff"]))
):
    return await report_service.get_attendance_report(from_date, to_date)


@router.get("/reminders/")
async def get_reminders_report(
    current_user: dict = Depends(RoleChecker(["admin", "doctor", "pharmacist", "it_staff"]))
):
    return await report_service.get_reminders_report()
