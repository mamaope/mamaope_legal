"""
Utility functions for generating standardized API responses.
"""

import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import HTTPException
from mamaope_legal.schemas import StandardResponse, Metadata, ErrorResponse, SuccessResponse


def create_success_response(
    data: Any,
    status_code: int = 200,
    message: Optional[str] = None,
    execution_time: Optional[float] = None,
    additional_details: Optional[Dict[str, Any]] = None
) -> StandardResponse:
    """Create a standardized success response."""
    
    # Wrap data in success response if it's not already wrapped
    if not isinstance(data, SuccessResponse) and message:
        wrapped_data = SuccessResponse(
            message=message,
            details=additional_details
        )
    else:
        wrapped_data = data
    
    metadata = Metadata(
        statusCode=status_code,
        errors=[],
        executionTime=execution_time or 0.0,
        timestamp=datetime.utcnow()
    )
    
    return StandardResponse(
        data=wrapped_data,
        metadata=metadata,
        success=1
    )


def create_error_response(
    message: str,
    status_code: int = 400,
    errors: Optional[List[str]] = None,
    execution_time: Optional[float] = None,
    additional_details: Optional[Dict[str, Any]] = None
) -> StandardResponse:
    """Create a standardized error response."""
    
    error_data = ErrorResponse(
        message=message,
        details=additional_details
    )
    
    metadata = Metadata(
        statusCode=status_code,
        errors=errors or [message],
        executionTime=execution_time or 0.0,
        timestamp=datetime.utcnow()
    )
    
    return StandardResponse(
        data=error_data,
        metadata=metadata,
        success=0
    )


def create_http_exception(
    message: str,
    status_code: int = 400,
    errors: Optional[List[str]] = None,
    execution_time: Optional[float] = None,
    additional_details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create an HTTPException with standardized error response."""
    
    error_response = create_error_response(
        message=message,
        status_code=status_code,
        errors=errors,
        execution_time=execution_time,
        additional_details=additional_details
    )
    
    return HTTPException(
        status_code=status_code,
        detail=error_response.model_dump(mode='json')
    )


class ResponseTimer:
    """Context manager for measuring execution time."""
    
    def __init__(self):
        self.start_time = None
        self.execution_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.execution_time = time.time() - self.start_time
    
    def get_execution_time(self) -> float:
        """Get the execution time."""
        if self.execution_time is None:
            return time.time() - self.start_time
        return self.execution_time
