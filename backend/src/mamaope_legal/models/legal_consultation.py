"""
Legal Consultation Session and Chat Message models for Mamaope Legal AI.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from mamaope_legal.models.base import Base


class LegalConsultation(Base):
    """
    Represents a legal consultation session between a user and the AI system.
    Each session can have multiple chat messages.
    """
    __tablename__ = "legal_consultations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_name = Column(String(255), nullable=True)
    case_summary = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(String, nullable=True, default=lambda: datetime.utcnow().isoformat())
    updated_at = Column(String, nullable=True, default=lambda: datetime.utcnow().isoformat())

    # Relationships
    user = relationship("User", back_populates="legal_consultations")
    chat_messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LegalConsultation(id={self.id}, user_id={self.user_id}, name='{self.session_name}')>"


class ChatMessage(Base):
    """
    Represents a message in a legal consultation chat session.
    Can be from the user (legal professional) or the AI assistant.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("legal_consultations.id"), nullable=False, index=True)
    message_type = Column(String(20), nullable=False)  # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)
    case_data = Column(Text, nullable=True)
    analysis_complete = Column(Boolean, nullable=False, default=False)
    created_at = Column(String, nullable=True, default=lambda: datetime.utcnow().isoformat())

    # Relationships
    session = relationship("LegalConsultation", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, type='{self.message_type}')>"