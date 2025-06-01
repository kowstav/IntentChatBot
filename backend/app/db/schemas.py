from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MessageBase(BaseModel):
    content: str
    sender: str
    intent: Optional[str] = None
    confidence: Optional[float] = None

class MessageCreate(MessageBase):
    conversation_id: int

class Message(MessageBase):
    id: int
    timestamp: datetime
    conversation_id: int

    class Config:
        orm_mode = True

class ConversationBase(BaseModel):
    user_id: Optional[str] = None
    escalated: bool = False

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    messages: List[Message] = []

    class Config:
        orm_mode = True

class EscalationTicketBase(BaseModel):
    status: str
    assigned_agent: Optional[str] = None

class EscalationTicketCreate(EscalationTicketBase):
    conversation_id: int

class EscalationTicket(EscalationTicketBase):
    id: int
    created_at: datetime
    conversation_id: int

    class Config:
        orm_mode = True