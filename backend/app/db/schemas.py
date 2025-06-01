# backend/app/db/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Message Schemas ---
class MessageBase(BaseModel):
    content: str
    sender: str # 'user' or 'bot' or 'system'
    intent: Optional[str] = None
    confidence: Optional[float] = None

class MessageCreate(MessageBase):
    conversation_id: int

class Message(MessageBase):
    id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    conversation_id: int

    class Config:
        orm_mode = True

# --- Conversation Schemas ---
class ConversationBase(BaseModel):
    user_id: Optional[str] = None # Can be an external user ID
    escalated: bool = False

class ConversationCreate(ConversationBase):
    pass # user_id is optional at creation

class Conversation(ConversationBase):
    id: int
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    messages: List[Message] = [] # To hold associated messages when querying

    class Config:
        orm_mode = True

# --- Escalation Ticket Schemas ---
class EscalationTicketBase(BaseModel):
    status: str # e.g., 'pending', 'open', 'resolved', 'closed'
    assigned_agent: Optional[str] = None

class EscalationTicketCreate(EscalationTicketBase):
    conversation_id: int
    # initial_query: Optional[str] = None # Could be added from escalation logic

class EscalationTicket(EscalationTicketBase):
    id: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    conversation_id: int
    # conversation: Optional[Conversation] = None # If you want to nest it

    class Config:
        orm_mode = True

# --- Chat Endpoint Schemas ---
class ChatPayload(BaseModel): # Already implicitly defined in chatbot.py, but good to have it here
    text: str
    user_id: Optional[str] = None
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    conversation_id: int
    user_message_id: int # ID of the user's message in the DB
    intent: Optional[str]
    confidence: Optional[float]
    entities: Dict[str, Any]
    requires_human_escalation: bool
    response: str # The bot's textual response
    bot_message_id: Optional[int] = None # ID of the bot's response message in the DB
    escalation_ticket_id: Optional[int] = None

    class Config:
        orm_mode = True # If you ever construct this from an ORM model directly

# --- Feedback Schemas (Example, if you implement a feedback endpoint) ---
class FeedbackCreate(BaseModel):
    session_id: Optional[str] = None # Or conversation_id
    # chat_log_id: Optional[int] = None # Or message_id for specific message feedback
    rating: int = Field(..., ge=1, le=5) # Rating from 1 to 5
    comment: Optional[str] = None
    # Add other relevant fields like message_id, intent_at_time_of_feedback etc.

class Feedback(FeedbackCreate):
    id: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True