"""
Main FastAPI application for Mamaope Legal AI.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from mamaope_legal.core.config import get_config
from mamaope_legal.core.response_utils import create_success_response, create_error_response, ResponseTimer
from mamaope_legal.schemas import StandardResponse
from mamaope_legal.api.v1 import auth, legal_consultation, chat_sessions

config = get_config()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Mamaope Legal AI application...")
    try:
        from mamaope_legal.core.database import initialize_database
        initialize_database()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.warning(f"Database initialization failed during startup: {e}")
        logger.info("Application will continue - database will be initialized on first access")
    
    try:
        from mamaope_legal.services.vectorstore_manager import initialize_vectorstore
        initialize_vectorstore()
        logger.info("Vector store initialization completed")
    except Exception as e:
        logger.warning(f"Vector store initialization failed during startup: {e}")
        logger.info("Application will continue - AI will work without RAG context")
    
    try:
        from mamaope_legal.services.genai_client import initialize_genai_client
        initialize_genai_client()
        logger.info("GenAI client initialization completed")
    except Exception as e:
        logger.warning(f"GenAI client initialization failed during startup: {e}")
        logger.info("Application will continue - AI functionality may be limited")
    
    logger.info("Application startup completed successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Mamaope Legal AI application...")


# Create FastAPI application
app = FastAPI(
    title=config.application.app_name,
    description=config.application.app_description,
    version=config.application.app_version,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    return response


# HTTPException handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    
    # Create standardized error response
    error_response = create_error_response(
        message=str(exc.detail),
        status_code=exc.status_code,
        errors=[str(exc.detail)],
        execution_time=0.0
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Create standardized error response
    error_response = create_error_response(
        message="Internal server error",
        status_code=500,
        errors=[str(exc)],
        execution_time=0.0
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
    )


# Health check endpoint
@app.get("/health", response_model=StandardResponse)
async def health_check():
    """Application health check."""
    with ResponseTimer() as timer:
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": config.application.app_version,
            "environment": config.application.environment
        }
        
        return create_success_response(
            data=health_data,
            status_code=200,
            execution_time=timer.get_execution_time()
        )

API_VERSION_PREFIX = "/api/v1"

# Include API routers
app.include_router(auth.router, prefix=f"{API_VERSION_PREFIX}/auth", tags=["Authentication"])
app.include_router(legal_consultation.router, prefix=f"{API_VERSION_PREFIX}/consult", tags=["Legal Consultation"])
app.include_router(chat_sessions.router, prefix=f"{API_VERSION_PREFIX}/chat", tags=["Chat Sessions"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.application.api_host,
        port=config.application.api_port,
        reload=config.application.debug,
        log_level=config.application.debug and "debug" or "info"
    )
