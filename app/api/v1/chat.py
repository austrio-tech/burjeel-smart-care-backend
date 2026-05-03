from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.schemas import ChatMessageResponse
from app.api.deps import get_current_user_websocket, get_current_active_user, RoleChecker
from app.core.supabase import supabase
from fastapi.concurrency import run_in_threadpool
from datetime import datetime

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
        if current_user["role"] in ["admin", "pharmacist", "it_staff"]:
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
