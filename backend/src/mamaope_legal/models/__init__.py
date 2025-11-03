"""
Database models.
"""

# Import all models to ensure they are registered with SQLAlchemy
from .base import Base
from .user import User
from .legal_consultation import LegalConsultation, ChatMessage

__all__ = ["Base", "User", "LegalConsultation", "ChatMessage"]