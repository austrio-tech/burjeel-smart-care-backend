from datetime import datetime
from typing import Optional, Dict, Any, List
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool

async def log_action(
    user_id: Optional[int],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    log_data = {
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "ip_address": ip_address,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    await run_in_threadpool(
        lambda: supabase.table("audit_logs").insert(log_data).execute()
    )

async def get_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    result = await run_in_threadpool(
        lambda: supabase.table("audit_logs").select("*").order("timestamp", desc=True).limit(limit).execute()
    )
    return result.data if result.data else []
