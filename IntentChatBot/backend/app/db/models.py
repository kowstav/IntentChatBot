from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    escalated = Column(Boolean, default=False)
    
    messages = relationship("Message", back_populates="conversation")
    ticket = relationship("EscalationTicket", back_populates="conversation", uselist=False)

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sender = Column(String)
    intent = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    
    conversation = relationship("Conversation", back_populates="messages")

class EscalationTicket(Base):
    __tablename__ = "escalation_tickets"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)
    assigned_agent = Column(String, nullable=True)
    
    conversation = relationship("Conversation", back_populates="ticket")