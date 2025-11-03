"""
Pydantic schemas for request/response validation.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, Generic, TypeVar, List
from datetime import datetime
import time

# Generic type for response data
T = TypeVar('T')

class Metadata(BaseModel):
    """Standard metadata for API responses."""
    statusCode: int = Field(..., description="HTTP status code")
    errors: List[str] = Field(default_factory=list, description="List of error messages")
    executionTime: float = Field(..., description="Request execution time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    def model_dump(self, **kwargs):
        """Custom model dump to handle datetime serialization."""
        data = super().model_dump(**kwargs)
        # Convert datetime to ISO string
        if isinstance(data.get('timestamp'), datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return data
    
    def model_dump_json(self, **kwargs):
        """Custom JSON dump to handle datetime serialization."""
        import json
        data = self.model_dump(**kwargs)
        return json.dumps(data, default=str)

class StandardResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    data: T = Field(..., description="Response data")
    metadata: Metadata = Field(..., description="Response metadata")
    success: int = Field(..., description="Success indicator (1 for success, 0 for failure)")

class ErrorResponse(BaseModel):
    """Error response schema."""
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

class SuccessResponse(BaseModel):
    """Success response schema."""
    message: str = Field(..., description="Success message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional success details")


class LegalQueryInput(BaseModel):
    """Input schema for legal consultation requests."""
    case_data: str = Field(..., min_length=10, max_length=10000, description="Legal case data for analysis")
    chat_history: Optional[str] = Field(default="", max_length=50000, description="Previous conversation history")
    session_id: Optional[int] = Field(None, description="Chat session ID to store the conversation")


class LegalQueryResponse(BaseModel):
    """Response schema for legal consultation results."""
    model_response: str = Field(..., description="AI model response")
    analysis_complete: bool = Field(..., description="Whether legal analysis is complete")
    updated_chat_history: str = Field(..., description="Updated conversation history")
    session_id: Optional[int] = Field(None, description="Chat session ID if conversation was stored")
    message_id: Optional[int] = Field(None, description="Message ID of the AI response if stored")
    prompt_type: Optional[str] = Field(None, description="Type of prompt used (legal_analysis, case_law, legal_guidance)")


# Chat Session Management Schemas
class ChatSessionCreate(BaseModel):
    """Schema for creating a new chat session."""
    session_name: Optional[str] = Field(None, max_length=255, description="Name for the chat session")
    case_summary: Optional[str] = Field(None, max_length=1000, description="Brief case summary")


class ChatSessionUpdate(BaseModel):
    """Schema for updating a chat session."""
    session_name: Optional[str] = Field(None, max_length=255, description="Name for the chat session")
    case_summary: Optional[str] = Field(None, max_length=1000, description="Brief case summary")
    is_active: Optional[bool] = Field(None, description="Whether the session is active")


class ChatSessionResponse(BaseModel):
    """Schema for chat session responses."""
    id: int
    user_id: int
    session_name: Optional[str]
    case_summary: Optional[str]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    message_count: Optional[int] = Field(default=0, description="Number of messages in the session")


class ChatMessageCreate(BaseModel):
    """Schema for creating a new chat message."""
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    message_type: str = Field(..., description="Type of message: 'user', 'assistant', or 'system'")
    case_data: Optional[str] = Field(None, max_length=10000, description="Legal case data associated with the message")
    analysis_complete: Optional[bool] = Field(default=False, description="Whether legal analysis is complete")


class ChatMessageResponse(BaseModel):
    """Schema for chat message responses."""
    id: int
    session_id: int
    message_type: str
    content: str
    case_data: Optional[str]
    analysis_complete: bool
    created_at: Optional[str]


class ChatSessionWithMessages(ChatSessionResponse):
    """Schema for chat session with messages."""
    messages: List[ChatMessageResponse] = Field(default_factory=list, description="Messages in the session")


class ChatSessionListResponse(BaseModel):
    """Schema for listing chat sessions."""
    sessions: List[ChatSessionResponse]
    total: int
    page: int
    per_page: int


class UserCreate(BaseModel):
    """Schema for user creation."""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    first_name: Optional[str] = Field(None, max_length=50, description="First name")
    last_name: Optional[str] = Field(None, max_length=50, description="Last name")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=12, max_length=128, description="Password")
    role: str = Field(default="user", description="User role")
    
    def model_post_init(self, __context):
        """Generate username and full_name from first_name and last_name if not provided."""
        if not self.username and self.first_name and self.last_name:
            # Generate username from first and last name with timestamp for uniqueness
            from datetime import datetime
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            self.username = f"{self.first_name.lower()}.{self.last_name.lower()}.{timestamp}"
        
        if not self.full_name and self.first_name and self.last_name:
            # Generate full_name from first and last name
            self.full_name = f"{self.first_name} {self.last_name}"


class UserUpdate(BaseModel):
    """Schema for user updates."""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = Field(None)
    role: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


class UserResponse(BaseModel):
    """Schema for user responses."""
    id: int
    username: str
    full_name: Optional[str]
    email: str
    role: str
    is_active: bool
    is_email_verified: bool
    created_at: Optional[str]
    updated_at: Optional[str]


class Token(BaseModel):
    """Schema for authentication tokens."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Schema for login requests."""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class LoginFormRequest(BaseModel):
    """Schema for OAuth2 form-based login requests."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class EmailVerificationRequest(BaseModel):
    """Schema for email verification requests."""
    token: str = Field(..., description="Email verification token")


class ResendVerificationRequest(BaseModel):
    """Schema for resending verification email requests."""
    email: EmailStr = Field(..., description="Email address to resend verification to")


class HealthCheckResponse(BaseModel):
    """Schema for health check responses."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="2.0.0", description="API version")
    services: Dict[str, Any] = Field(default_factory=dict, description="Service statuses")