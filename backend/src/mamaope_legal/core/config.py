"""
Configuration management for mamaope_legal AI CDSS.

This module provides secure configuration management following medical software
standards with proper environment variable handling and validation.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseSettings):
    """Database configuration with security validation."""
    
    # Database connection settings
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(..., env="DB_NAME")
    
    # Connection pool settings
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
    @field_validator('db_password')
    @classmethod
    def validate_db_password(cls, v):
        """Validate database password strength."""
        if v == 'password' or len(v) < 8:
            raise ValueError('Database password must be at least 8 characters and not be "password"')
        return v
    
    @field_validator('db_port')
    @classmethod
    def validate_db_port(cls, v):
        """Validate database port."""
        if not 1 <= v <= 65535:
            raise ValueError('Database port must be between 1 and 65535')
        return v
    
    @property
    def database_url(self) -> str:
        """Get database URL."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


class SecurityConfig(BaseSettings):
    """Security configuration with validation."""
    
    # JWT settings
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Encryption
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    
    # Password settings
    min_password_length: int = Field(default=12, env="MIN_PASSWORD_LENGTH")
    max_password_length: int = Field(default=128, env="MAX_PASSWORD_LENGTH")
    
    # Rate limiting
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    login_lockout_minutes: int = Field(default=15, env="LOGIN_LOCKOUT_MINUTES")
    
    @field_validator('secret_key')
    def validate_secret_key(cls, v):
        """Validate secret key strength."""
        if v == 'supersecretkey' or len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters and not be the default')
        return v
    
    @field_validator('encryption_key')
    def validate_encryption_key(cls, v):
        """Validate encryption key."""
        if len(v) < 32:
            raise ValueError('Encryption key must be at least 32 characters')
        return v


class ApplicationConfig(BaseSettings):
    """Main application configuration."""
    
    # Application settings
    app_name: str = Field(default="mamaope_legal AI CDSS", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    app_description: str = Field(default="AI Clinical Decision Support System", env="APP_DESCRIPTION")
    environment: str = Field(default="development", env="ENV")
    debug: bool = Field(default=False, env="DEBUG")
    
    # API settings
    api_root_path: str = Field(default="/api/v1", env="API_ROOT_PATH")
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8050, env="API_PORT")
    
    # Data limits
    max_patient_data_length: int = Field(default=10000, env="MAX_PATIENT_DATA_LENGTH")
    max_chat_history_length: int = Field(default=50000, env="MAX_CHAT_HISTORY_LENGTH")
    max_query_length: int = Field(default=2000, env="MAX_QUERY_LENGTH")
    
    @field_validator('environment')
    def validate_environment(cls, v):
        """Validate environment setting."""
        valid_envs = ['development', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v
    
    @field_validator('api_port')
    def validate_api_port(cls, v):
        """Validate API port."""
        if not 1 <= v <= 65535:
            raise ValueError('API port must be between 1 and 65535')
        return v


class Config:
    """Main configuration class that combines all config sections."""
    
    def __init__(self):
        """Initialize configuration with validation."""
        try:
            self.database = DatabaseConfig()
            self.security = SecurityConfig()
            self.application = ApplicationConfig()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    def get_database_url(self) -> str:
        """Get database URL."""
        return self.database.database_url
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.application.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.application.environment == 'development'


# Global configuration instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config
