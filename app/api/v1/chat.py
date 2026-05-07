from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.schemas import ChatMessageResponse
from app.api.deps import get_current_user_websocket, get_current_active_user, RoleChecker
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool
from datetime import datetime
from pydantic import BaseModel
from app.schemas.chat_message import ChatMessageCreate
import asyncio
from app.core.gmail_service import send_google_email
from app.services.reminder_service import get_template
from app.services.auth_service import get_user_by_id

async def send_chat_notification(sender: dict, receiver_id: int):
    try:
        receiver = await get_user_by_id(receiver_id)
        if not receiver or not receiver.get("email"):
            return
            
        # Get unread message count for receiver
        result = await run_in_threadpool(
            lambda: supabase.table("chat_messages")
            .select("message_id", count="exact")
            .eq("receiver_id", receiver_id)
            .eq("is_read", False)
            .execute()
        )
        
        unread_count = result.count if hasattr(result, 'count') and result.count is not None else 1
        
        email_html = get_template(
            "chat_notification",
            ext="html",
            recipient_name=receiver.get("username", "User"),
            sender_role=sender.get("role", "User").capitalize(),
            sender_name=sender.get("username", "Someone"),
            unread_count=unread_count
        )
        
        # send_google_email handles retries or we just fire it
        await run_in_threadpool(send_google_email, [receiver["email"]], "New Chat Message - Burjeel Smart Care", email_html)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to send chat notification: {str(e)}")


router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int
):
    current_user = await get_current_user_websocket(websocket)
    if not current_user:
        return
    
    await manager.connect(websocket, current_user["user_id"])
    
    try:
        while True:
            data = await websocket.receive_json()
            
            receiver_id = data.get("receiver_id")
            message_text = data.get("message_text")
            
            if message_text:
                message_data = {
                    "sender_id": current_user["user_id"],
                    "receiver_id": receiver_id,
                    "message_text": message_text,
                    "created_by": current_user["user_id"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "is_read": False
                }
                
                result = await run_in_threadpool(
                    lambda: supabase.table("chat_messages").insert(message_data).execute()
                )
                db_message = result.data[0] if result.data else {}
                
                message_response = {
                    "message_id": db_message.get("message_id"),
                    "sender_id": db_message.get("sender_id"),
                    "receiver_id": db_message.get("receiver_id"),
                    "message_text": db_message.get("message_text"),
                    "timestamp": db_message.get("timestamp"),
                    "is_read": db_message.get("is_read")
                }
                
                await manager.send_personal_message(message_response, current_user["user_id"])
                
                if receiver_id:
                    await manager.send_personal_message(message_response, receiver_id)
                    asyncio.create_task(send_chat_notification(current_user, receiver_id))
                    
    except WebSocketDisconnect:
        manager.disconnect(current_user["user_id"])


@router.get("/messages/", response_model=List[ChatMessageResponse])
async def get_chat_messages(
    with_user_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user)
):
    if with_user_id:
        # Get messages between current user and with_user_id
        result = await run_in_threadpool(
            lambda: supabase.table("chat_messages")
            .select("*")
            .or_(f"and(sender_id.eq.{current_user['user_id']},receiver_id.eq.{with_user_id}),and(sender_id.eq.{with_user_id},receiver_id.eq.{current_user['user_id']})")
            .order("timestamp")
            .execute()
        )
    else:
        if current_user["role"] in ["admin", "doctor", "pharmacist", "it_staff"]:
            result = await run_in_threadpool(
                lambda: supabase.table("chat_messages").select("*").order("timestamp").execute()
            )
        else:
            # Patients only see their own messages
            result = await run_in_threadpool(
                lambda: supabase.table("chat_messages")
                .select("*")
                .or_(f"sender_id.eq.{current_user['user_id']},receiver_id.eq.{current_user['user_id']}")
                .order("timestamp")
                .execute()
            )
            
            
    return result.data

@router.post("/messages/", response_model=ChatMessageResponse)
async def create_chat_message(
    message_in: ChatMessageCreate,
    current_user: dict = Depends(get_current_active_user)
):
    message_data = {
        "sender_id": current_user["user_id"],
        "receiver_id": message_in.receiver_id,
        "message_text": message_in.message_text,
        "created_by": current_user["user_id"],
        "timestamp": datetime.utcnow().isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "is_read": False
    }
    
    result = await run_in_threadpool(
        lambda: supabase.table("chat_messages").insert(message_data).execute()
    )
    
    db_message = result.data[0] if result.data else {}
    if message_in.receiver_id:
        asyncio.create_task(send_chat_notification(current_user, message_in.receiver_id))
    return db_message

class MarkReadRequest(BaseModel):
    sender_id: int

@router.put("/messages/read")
async def mark_messages_read(
    request: MarkReadRequest,
    current_user: dict = Depends(get_current_active_user)
):
    result = await run_in_threadpool(
        lambda: supabase.table("chat_messages")
        .update({"is_read": True})
        .eq("sender_id", request.sender_id)
        .eq("receiver_id", current_user["user_id"])
        .execute()
    )
    return {"success": True, "marked_count": len(result.data) if result.data else 0}
