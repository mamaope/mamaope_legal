"""
User model for Mamaope Legal AI.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class User(Base):
    """User model with role-based access control."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String(255), nullable=True)
    role = Column(String(20), default="user", nullable=False)
    created_at = Column(String, nullable=True)  # Will store ISO datetime string
    updated_at = Column(String, nullable=True)  # Will store ISO datetime string
    
    # Relationship to legal consultations
    legal_consultations = relationship("LegalConsultation", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def created_at_str(self) -> str:
        """Ensure created_at is returned as string."""
        return str(self.created_at) if self.created_at else ""
    
    @property
    def updated_at_str(self) -> str:
        """Ensure updated_at is returned as string."""
        return str(self.updated_at) if self.updated_at else ""
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}', role='{self.role}', active={self.is_active})>"
    
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role in ["admin", "super_admin"]
    
    def is_super_admin(self) -> bool:
        """Check if user is a super admin."""
        return self.role == "super_admin"
