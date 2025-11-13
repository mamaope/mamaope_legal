import logging
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from mamaope_legal.core.database import get_db
from mamaope_legal.core.response_utils import create_success_response, create_error_response, ResponseTimer
from mamaope_legal.models.user import User
from mamaope_legal.schemas import LegalQueryInput, LegalQueryResponse, StandardResponse, SuccessResponse, ChatMessageCreate
from mamaope_legal.services.conversational_service import generate_response
from mamaope_legal.services.legal_consultation_service import LegalConsultationService
from mamaope_legal.api.v1.auth import require_user_role

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=StandardResponse)
async def legal_consultation_health():
    """
    Health check endpoint for the legal consultation service.
    Checks if the AI service is available and responding.
    """
    with ResponseTimer() as timer:
        try:
            # Test AI service with a simple query
            test_response, _, _ = await generate_response(
                query="test",
                chat_history="",
                patient_data="test patient data"
            )
            
            if test_response and len(test_response.strip()) > 0:
                health_data = {
                    "status": "healthy",
                    "ai_service": "available",
                    "message": "Legal consultation service is operational"
                }
                
                return create_success_response(
                    data=health_data,
                    status_code=200,
                    message="Legal consultation service is healthy",
                    execution_time=timer.get_execution_time()
                )
            else:
                return create_error_response(
                    message="AI service returned empty response",
                    status_code=503,
                    execution_time=timer.get_execution_time()
                )
                
        except Exception as e:
            logger.error(f"Diagnosis health check failed: {str(e)}")
            # Sanitize error message for security
            error_message = "AI service temporarily unavailable"
            if "database" in str(e).lower() or "connection" in str(e).lower():
                error_message = "Service temporarily unavailable"
            
            return create_error_response(
                message=error_message,
                status_code=503,
                execution_time=timer.get_execution_time()
            )


@router.post("/analyze", response_model=StandardResponse)
async def analyze_case(data: LegalQueryInput, current_user: User = Depends(require_user_role), db: Session = Depends(get_db)):
    """
    Generate AI-powered legal analysis based on case data.
    Requires authentication - only logged-in users can access this endpoint.
    """
    with ResponseTimer() as timer:
        try:
            # Validate input data
            if not data.case_data or len(data.case_data.strip()) < 10:
                return create_error_response(
                    message="Case data must be at least 10 characters long",
                    status_code=400,
                    execution_time=timer.get_execution_time()
                )

            logger.info(f"Legal analysis request from user: {current_user.username} (role: {current_user.role})")
            logger.info(f"Case data length: {len(data.case_data)} characters")

            # Get chat history from session if session_id is provided
            chat_history = data.chat_history or ""
            session_id = data.session_id
            message_id = None
            
            # Initialize session service
            session_service = LegalConsultationService(db)
            
            if session_id:
                try:
                    chat_history = session_service.get_chat_history(session_id, current_user)
                except Exception as e:
                    logger.warning(f"Could not get chat history from session {session_id}: {e}")
                    # Continue with provided chat_history
            else:
                # Auto-create a new session if none provided
                try:
                    from mamaope_legal.schemas import ChatSessionCreate
                    new_session_data = ChatSessionCreate(
                        session_name=f"Legal Consultation - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                        case_summary=data.case_data[:200] + "..." if len(data.case_data) > 200 else data.case_data
                    )
                    new_session = session_service.create_session(current_user, new_session_data)
                    session_id = new_session.id
                    logger.info(f"Auto-created new case session {session_id} for user {current_user.id}")
                except Exception as e:
                    logger.warning(f"Could not auto-create session: {e}")
                    # Continue without session

            # Use the real AI service to generate response
            try:
                response, sources, prompt_type = await generate_response(
                    query=data.case_data,
                    chat_history=chat_history,
                    case_data=data.case_data
                )
                logger.info(f"🎯 Prompt type used: {prompt_type}")
                # Validate AI response
                if not response or len(response.strip()) < 10:
                    return create_error_response(
                        message="AI service returned insufficient response. Please try again.",
                        status_code=503,
                        execution_time=timer.get_execution_time()
                    )
                # Determine if analysis is complete based on prompt_type
                analysis_complete = (prompt_type == "success")
                    
            except Exception as ai_error:
                logger.error(f"AI service error: {str(ai_error)}")
                return create_error_response(
                    message=f"AI service is currently unavailable. Error: {str(ai_error)}",
                    status_code=503,
                    execution_time=timer.get_execution_time()
                )

            # Store messages in session (session should exist now)
            if session_id:
                try:
                    # Add user message
                    user_message = ChatMessageCreate(
                        content=data.case_data,
                        message_type="user",
                        case_data=data.case_data,
                        analysis_complete=False
                    )
                    session_service.add_message(session_id, current_user, user_message)
                    
                    # Add AI response message
                    ai_message = ChatMessageCreate(
                        content=response,
                        message_type="assistant",
                        case_data=data.case_data,
                        analysis_complete=analysis_complete
                    )
                    ai_msg_response = session_service.add_message(session_id, current_user, ai_message)
                    message_id = ai_msg_response.id if ai_msg_response else None
                    
                    logger.info(f"Stored messages in session {session_id}, message_id: {message_id}")
                    
                except Exception as e:
                    logger.warning(f"Could not store messages in session {session_id}: {e}")
                    # Continue without storing

            # Build updated chat history
            updated_chat_history = (
                f"{chat_history}\nLawyer: {data.case_data}\nAI Assistant: {response}"
                if chat_history else
                f"Lawyer: {data.case_data}\nAI Assistant: {response}"
            )

            logger.info(f"AI legal analysis completed successfully. Response length: {len(response)} characters")
            
            legal_data = LegalQueryResponse(
                model_response=response,
                analysis_complete=analysis_complete,
                updated_chat_history=updated_chat_history,
                session_id=session_id,
                message_id=message_id,
                prompt_type=prompt_type
            )
            
            return create_success_response(
                data=legal_data,
                status_code=200,
                execution_time=timer.get_execution_time()
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in case endpoint: {str(e)}")
            # Sanitize error message for security
            error_message = "Case generation failed"
            if "database" in str(e).lower() or "connection" in str(e).lower():
                error_message = "Service temporarily unavailable"
            elif "ai" in str(e).lower() or "model" in str(e).lower():
                error_message = "AI service temporarily unavailable"
            
            return create_error_response(
                message=error_message,
                status_code=500,
                execution_time=timer.get_execution_time()
            )
