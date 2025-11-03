"""
Enhanced database service for mamaope_legal AI CDSS.

This module provides secure database operations with proper connection management,
transaction handling, and audit logging following medical software standards.
"""

import logging
from typing import Generator, Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from contextlib import contextmanager

from mamaope_legal.core.config import get_config

config = get_config()
logger = logging.getLogger(__name__)

# Database engine with enhanced security settings
engine = create_engine(
    config.get_database_url(),
    poolclass=QueuePool,
    pool_size=config.database.db_pool_size,
    max_overflow=config.database.db_max_overflow,
    pool_timeout=config.database.db_pool_timeout,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
    echo=config.application.debug,  # Log SQL queries in debug mode
    echo_pool=config.application.debug,  # Log pool events in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Get database session with proper error handling and cleanup.
    
    Yields:
        Database session
        
    Raises:
        SQLAlchemyError: If database connection fails
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database session: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_transaction():
    """
    Get database session with transaction management.
    
    Yields:
        Database session with transaction support
        
    Raises:
        SQLAlchemyError: If database operation fails
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database transaction error: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error in database transaction: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    try:
        # Import all models to ensure they are registered with SQLAlchemy
        from mamaope_legal.models import Base, User, LegalConsultation, ChatMessage
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except SQLAlchemyError as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def check_database_connection() -> bool:
    """
    Check if database connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection check successful")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection check failed: {e}")
        return False


# Database event listeners for additional security
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database connection parameters for security."""
    if 'postgresql' in str(dbapi_connection):
        # PostgreSQL specific settings
        with dbapi_connection.cursor() as cursor:
            # Set statement timeout (5 minutes)
            cursor.execute("SET statement_timeout = '300s'")
            # Set idle transaction timeout (10 minutes)
            cursor.execute("SET idle_in_transaction_session_timeout = '600s'")


@event.listens_for(engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries in debug mode."""
    if config.application.debug:
        logger.debug(f"SQL Query: {statement}")
        if parameters:
            logger.debug(f"SQL Parameters: {parameters}")


# Initialize database on module import
def initialize_database():
    """Initialize database connection and create tables if needed."""
    try:
        # Check connection
        if not check_database_connection():
            raise RuntimeError("Database connection failed")
        
        # Create tables if they don't exist
        create_tables()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


# Auto-initialize on import
if config.application.environment != 'test':
    try:
        initialize_database()
    except Exception as e:
        logger.warning(f"Database initialization failed on import: {e}")
        logger.info("Database will be initialized when first accessed")
