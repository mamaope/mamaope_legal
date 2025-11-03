# """
# Model Configuration Module for mamaope_legal AI CDSS.

# This module handles AI model configurations and settings.
# """

# import os
# import logging
# from typing import Dict, Optional, Any
# from dataclasses import dataclass
# from enum import Enum

# logger = logging.getLogger(__name__)


# class ModelProvider(Enum):
#     """AI model providers."""
#     VERTEX_AI = "vertex_ai"
#     OPENAI = "openai"
#     AZURE_OPENAI = "azure_openai"


# @dataclass
# class ModelConfig:
#     """Configuration for an AI model."""
#     provider: ModelProvider
#     model_name: str
#     max_tokens: int
#     temperature: float
#     top_p: float
#     top_k: int
#     safety_settings: Dict[str, Any]


# class ModelManager:
#     """Manages AI model configurations."""
    
#     def __init__(self):
#         """Initialize the model manager."""
#         self.models: Dict[str, ModelConfig] = {}
#         self.default_model = "gemini-2.5-flash"
#         self._load_models()
    
#     def _load_models(self) -> None:
#         """Load model configurations."""
#         logger.info("Loading model configurations...")
        
#         # Default models
#         self.models = {
#             "gemini-2.5-flash": ModelConfig(
#                 provider=ModelProvider.VERTEX_AI,
#                 model_name="gemini-2.5-flash",
#                 max_tokens=4000,
#                 temperature=0.1,
#                 top_p=0.8,
#                 top_k=40,
#                 safety_settings={}
#             ),
#             "gemini-pro": ModelConfig(
#                 provider=ModelProvider.VERTEX_AI,
#                 model_name="gemini-2.5-flash",
#                 max_tokens=4000,
#                 temperature=0.1,
#                 top_p=0.8,
#                 top_k=40,
#                 safety_settings={}
#             ),
#             "gpt-4": ModelConfig(
#                 provider=ModelProvider.OPENAI,
#                 model_name="gemini-2.5-flash",
#                 max_tokens=4000,
#                 temperature=0.1,
#                 top_p=0.8,
#                 top_k=40,
#                 safety_settings={}
#             )
#         }
        
#         logger.info(f"Loaded {len(self.models)} model configurations")
    
#     def get_model(self, model_name: str) -> Optional[ModelConfig]:
#         """Get model configuration by name."""
#         return self.models.get(model_name)
    
#     def get_default_model(self) -> ModelConfig:
#         """Get the default model configuration."""
#         return self.models.get(self.default_model, self.models["gemini-2.5-flash"])
    
#     def get_all_models(self) -> Dict[str, ModelConfig]:
#         """Get all model configurations."""
#         return self.models.copy()
    
#     def get_vertex_ai_config(self) -> Dict[str, Any]:
#         """Get Vertex AI configuration."""
#         return {
#             "project": os.getenv("GOOGLE_CLOUD_PROJECT", "regal-autonomy-454806-d1"),
#             "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
#             "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "/app/regal-autonomy-454806-d1-edf68610c57a.json")
#         }


# # Global model manager instance
# _model_manager: Optional[ModelManager] = None


# def get_model_manager() -> ModelManager:
#     """Get the global model manager instance."""
#     global _model_manager
#     if _model_manager is None:
#         _model_manager = ModelManager()
#     return _model_manager



