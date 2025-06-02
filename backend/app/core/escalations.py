# backend/app/core/escalations.py
from sqlalchemy.orm import Session
from ..db import models, schemas # Assuming models.py and schemas.py are in backend/app/db/
from ..config import settings
from datetime import datetime

def create_escalation_ticket(db: Session, conversation_id: int, user_id: str | None = None, initial_query: str | None = None) -> models.EscalationTicket:
    """
    Creates and stores an escalation ticket.
    """
    # First, ensure the conversation exists and mark it as escalated
    db_conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if not db_conversation:
        pass
    if db_conversation:
        db_conversation.escalated = True
        db_conversation.end_time = datetime.utcnow() # Or keep it open for agent

    # Create the escalation ticket
    ticket_data = schemas.EscalationTicketCreate(
        conversation_id=conversation_id,
        status="pending" # Initial status
        # assigned_agent can be set later
    )
    db_ticket = models.EscalationTicket(**ticket_data.model_dump(), created_at=datetime.utcnow())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    
    # Here  would also typically push this ticket ID or details to a Redis queue
    # for human agents to pick up.
    # Example (conceptual, actual Redis client usage would be here):
    # print(f"LOG: Pushing ticket {db_ticket.id} for conversation {conversation_id} to Redis.")

    return db_ticket

def handle_escalation(message_text: str, user_id: str | None, db: Session, conversation_id: int) -> models.EscalationTicket:
    """
    Handles the escalation process for a given message.
    This would involve:
    1. Logging the message that triggered escalation (if not already done).
    2. Creating an escalation ticket.
    3. Notifying relevant systems (e.g., pushing to Redis queue).
    """
    print(f"Escalation triggered for user '{user_id}' due to message: '{message_text}' in conversation {conversation_id}")

    # For simplicity, we'll directly create a ticket here.
    # In a real app,  might have more complex logic to decide if a new conversation
    # needs to be created or an existing one is used.
    
    ticket = create_escalation_ticket(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        initial_query=message_text
    )
    return ticket