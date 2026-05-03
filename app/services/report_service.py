from datetime import date
from typing import Optional, Dict, Any
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool

async def get_attendance_report(
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Dict[str, Any]:
    query = supabase.table("attendance").select("status")
    
    if from_date:
        query = query.gte("appointment_date", from_date.isoformat())
    if to_date:
        query = query.lte("appointment_date", to_date.isoformat())
    
    result = await run_in_threadpool(lambda: query.execute())
    data = result.data
    
    report = {"came": 0, "not came": 0}
    for item in data:
        status = item.get("status")
        if status in report:
            report[status] += 1
    
    total = sum(report.values())
    attendance_rate = (report["came"] / total * 100) if total > 0 else 0
    
    return {
        **report,
        "total_attendances": total,
        "attendance_rate": round(attendance_rate, 2)
    }


async def get_reminders_report() -> Dict[str, Any]:
    result = await run_in_threadpool(
        lambda: supabase.table("reminders").select("sent_status").execute()
    )
    data = result.data
    
    report = {"pending": 0, "sent": 0, "failed": 0}
    for item in data:
        status = item.get("sent_status")
        if status in report:
            report[status] += 1
    
    total = len(data)
    success_rate = (report["sent"] / total * 100) if total > 0 else 0
    
    return {
        **report,
        "total": total,
        "success_rate": round(success_rate, 2)
    }
