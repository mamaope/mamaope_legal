"""
Simplified Configuration for mamaope_legal AI CDSS.

This module provides a clean, easy-to-use configuration system
that focuses on essential settings without unnecessary complexity.
"""

import os
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class SimpleAIConfig(BaseModel):
    """Simplified AI configuration."""
    
    # Model settings
    model_name: str = Field(default="gemini-2.5-flash", env="AI_MODEL")
    project_id: str = Field(default="regal-autonomy-454806-d1", env="GOOGLE_CLOUD_PROJECT")
    location: str = Field(default="us-central1", env="GOOGLE_CLOUD_LOCATION")
    
    # Generation settings
    max_tokens: int = Field(default=3000, env="AI_MAX_TOKENS")
    max_context_length: int = Field(default=3000, env="AI_MAX_CONTEXT_LENGTH")
    max_sources: int = Field(default=5, env="AI_MAX_SOURCES")
    
    # Temperature settings for different query types
    drug_info_temperature: float = Field(default=0.2, env="AI_DRUG_TEMPERATURE")
    diagnosis_temperature: float = Field(default=0.4, env="AI_DIAGNOSIS_TEMPERATURE")
    general_temperature: float = Field(default=0.3, env="AI_GENERAL_TEMPERATURE")
    
    # Validation settings
    enable_validation: bool = Field(default=True, env="AI_ENABLE_VALIDATION")
    max_response_length: int = Field(default=10000, env="AI_MAX_RESPONSE_LENGTH")
    
    # Retry settings
    max_retries: int = Field(default=3, env="AI_MAX_RETRIES")
    retry_delay: float = Field(default=1.0, env="AI_RETRY_DELAY")


class SimpleConfig:
    """Main simplified configuration class."""
    
    def __init__(self):
        """Initialize configuration."""
        try:
            self.ai = SimpleAIConfig()
            logger.info("Simple configuration loaded successfully")
        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            raise
    
    def get_temperature(self, query_type: str) -> float:
        """Get temperature for query type."""
        if query_type == "drug_info":
            return self.ai.drug_info_temperature
        elif query_type == "diagnosis":
            return self.ai.diagnosis_temperature
        else:
            return self.ai.general_temperature
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "model_name": self.ai.model_name,
            "project_id": self.ai.project_id,
            "location": self.ai.location,
            "max_tokens": self.ai.max_tokens,
            "max_context_length": self.ai.max_context_length,
            "max_sources": self.ai.max_sources,
            "temperatures": {
                "drug_info": self.ai.drug_info_temperature,
                "diagnosis": self.ai.diagnosis_temperature,
                "general": self.ai.general_temperature
            },
            "validation": {
                "enabled": self.ai.enable_validation,
                "max_response_length": self.ai.max_response_length
            },
            "retry": {
                "max_retries": self.ai.max_retries,
                "retry_delay": self.ai.retry_delay
            }
        }


# Global configuration instance
simple_config = SimpleConfig()


def get_simple_config() -> SimpleConfig:
    """Get the global simplified configuration instance."""
    return simple_config

