import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from mamaope_legal.core.database import get_db
from mamaope_legal.core.response_utils import create_success_response, create_error_response, ResponseTimer
from mamaope_legal.models.user import User
from mamaope_legal.schemas import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse, 
    ChatMessageCreate, ChatMessageResponse, ChatSessionWithMessages,
    ChatSessionListResponse, StandardResponse
)
from mamaope_legal.services.legal_consultation_service import LegalConsultationService
from mamaope_legal.api.v1.auth import require_user_role

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions", response_model=StandardResponse, status_code=201)
async def create_chat_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(require_user_role),
    db: Session = Depends(get_db)
):
    """Create a new chat session."""
    with ResponseTimer() as timer:
        try:
            service = LegalConsultationService(db)
            session = service.create_session(current_user, session_data)
            
            return create_success_response(
                data=session,
                status_code=201,
                message="Chat session created successfully",
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            return create_error_response(
                message="Failed to create chat session",
                status_code=500,
                execution_time=timer.get_execution_time()
            )


@router.get("/sessions", response_model=StandardResponse)
async def list_chat_sessions(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(require_user_role),
    db: Session = Depends(get_db)
):
    """List chat sessions for the current user."""
    with ResponseTimer() as timer:
        try:
            service = LegalConsultationService(db)
            sessions = service.list_sessions(current_user, page, per_page)
            
            return create_success_response(
                data=sessions,
                status_code=200,
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Error listing chat sessions: {e}")
            return create_error_response(
                message="Failed to list chat sessions",
                status_code=500,
                execution_time=timer.get_execution_time()
            )


@router.get("/sessions/{session_id}", response_model=StandardResponse)
async def get_chat_session(
    session_id: int,
    current_user: User = Depends(require_user_role),
    db: Session = Depends(get_db)
):
    """Get a specific chat session."""
    with ResponseTimer() as timer:
        try:
            service = LegalConsultationService(db)
            session = service.get_session(session_id, current_user)
            
            if not session:
                return create_error_response(
                    message="Chat session not found",
                    status_code=404,
                    execution_time=timer.get_execution_time()
                )
            
            return create_success_response(
                data=session,
                status_code=200,
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Error getting chat session {session_id}: {e}")
            return create_error_response(
                message="Failed to get chat session",
                status_code=500,
                execution_time=timer.get_execution_time()
            )


@router.get("/sessions/{session_id}/messages", response_model=StandardResponse)
async def get_chat_session_with_messages(
    session_id: int,
    current_user: User = Depends(require_user_role),
    db: Session = Depends(get_db)
):
    """Get a chat session with all its messages."""
    with ResponseTimer() as timer:
        try:
            service = LegalConsultationService(db)
            session = service.get_session_with_messages(session_id, current_user)
            
            if not session:
                return create_error_response(
                    message="Chat session not found",
                    status_code=404,
                    execution_time=timer.get_execution_time()
                )
            
            return create_success_response(
                data=session,
                status_code=200,
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Error getting chat session with messages {session_id}: {e}")
            return create_error_response(
                message="Failed to get chat session with messages",
                status_code=500,
                execution_time=timer.get_execution_time()
            )


@router.put("/sessions/{session_id}", response_model=StandardResponse)
async def update_chat_session(
    session_id: int,
    update_data: ChatSessionUpdate,
    current_user: User = Depends(require_user_role),
    db: Session = Depends(get_db)
):
    """Update a chat session."""
    with ResponseTimer() as timer:
        try:
            service = LegalConsultationService(db)
            session = service.update_session(session_id, current_user, update_data)
            
            if not session:
                return create_error_response(
                    message="Chat session not found",
                    status_code=404,
                    execution_time=timer.get_execution_time()
                )
            
            return create_success_response(
                data=session,
                status_code=200,
                message="Chat session updated successfully",
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Error updating chat session {session_id}: {e}")
            return create_error_response(
                message="Failed to update chat session",
                status_code=500,
                execution_time=timer.get_execution_time()
            )


@router.delete("/sessions/{session_id}", response_model=StandardResponse)
async def delete_chat_session(
    session_id: int,
    current_user: User = Depends(require_user_role),
    db: Session = Depends(get_db)
):
    """Delete a chat session."""
    with ResponseTimer() as timer:
        try:
            service = LegalConsultationService(db)
            deleted = service.delete_session(session_id, current_user)
            
            if not deleted:
                return create_error_response(
                    message="Chat session not found",
                    status_code=404,
                    execution_time=timer.get_execution_time()
                )
            
            return create_success_response(
                data={"deleted": True},
                status_code=200,
                message="Chat session deleted successfully",
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Error deleting chat session {session_id}: {e}")
            return create_error_response(
                message="Failed to delete chat session",
                status_code=500,
                execution_time=timer.get_execution_time()
            )


@router.post("/sessions/{session_id}/messages", response_model=StandardResponse, status_code=201)
async def add_message_to_session(
    session_id: int,
    message_data: ChatMessageCreate,
    current_user: User = Depends(require_user_role),
    db: Session = Depends(get_db)
):
    """Add a message to a chat session."""
    with ResponseTimer() as timer:
        try:
            service = LegalConsultationService(db)
            message = service.add_message(session_id, current_user, message_data)
            
            if not message:
                return create_error_response(
                    message="Chat session not found",
                    status_code=404,
                    execution_time=timer.get_execution_time()
                )
            
            return create_success_response(
                data=message,
                status_code=201,
                message="Message added successfully",
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            return create_error_response(
                message="Failed to add message",
                status_code=500,
                execution_time=timer.get_execution_time()
            )


@router.get("/sessions/{session_id}/history", response_model=StandardResponse)
async def get_chat_history(
    session_id: int,
    current_user: User = Depends(require_user_role),
    db: Session = Depends(get_db)
):
    """Get formatted chat history for a session."""
    with ResponseTimer() as timer:
        try:
            service = LegalConsultationService(db)
            chat_history = service.get_chat_history(session_id, current_user)
            
            return create_success_response(
                data={"chat_history": chat_history},
                status_code=200,
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Error getting chat history for session {session_id}: {e}")
            return create_error_response(
                message="Failed to get chat history",
                status_code=500,
                execution_time=timer.get_execution_time()
            )









