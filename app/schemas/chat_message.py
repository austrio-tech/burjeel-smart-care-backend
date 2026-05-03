from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChatMessageBase(BaseModel):
    receiver_id: Optional[int] = None
    message_text: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageUpdate(BaseModel):
    is_read: Optional[bool] = None


class ChatMessageResponse(ChatMessageBase):
    message_id: int
    sender_id: int
    timestamp: datetime
    is_read: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
