"""
Reporting endpoints for the Burjeel Smart Care API.

This module exposes aggregated summary reports used for management dashboards.
All report endpoints are restricted to staff roles: admin, doctor, pharmacist, and it_staff.
Patients cannot access reports.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.services import report_service
from app.api.deps import get_current_active_user, RoleChecker

router = APIRouter()


@router.get("/attendance/")
async def get_attendance_report(
    # Query(...) declares these as optional URL parameters, e.g. ?from_date=2024-01-01
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(RoleChecker(["admin", "doctor", "pharmacist", "it_staff"]))
):
    """
    GET /reports/attendance/ — Admin, Doctor, Pharmacist, or IT Staff only.
    Returns an aggregated attendance report. Optionally filter by ?from_date and ?to_date
    to restrict the report to a specific date range.
    """
    return await report_service.get_attendance_report(from_date, to_date)


@router.get("/reminders/")
async def get_reminders_report(
    current_user: dict = Depends(RoleChecker(["admin", "doctor", "pharmacist", "it_staff"]))
):
    """
    GET /reports/reminders/ — Admin, Doctor, Pharmacist, or IT Staff only.
    Returns a summary report of all reminders, including delivery success and failure counts.
    """
    return await report_service.get_reminders_report()
