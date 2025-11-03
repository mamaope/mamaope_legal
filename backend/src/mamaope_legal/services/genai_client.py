"""
GenAI client initialization module.
This module handles the initialization of the Google GenAI client once at startup.
"""
import os
import logging
import traceback
from google import genai
from google.auth import load_credentials_from_file
import vertexai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Global client instance
_genai_client = None

def initialize_vertexai():
    """Initialize Vertex AI with proper authentication."""
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_ID")
        location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GCP_LOCATION")
        service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        logger.info(f"Initializing Vertex AI with project: {project_id}, location: {location}")
        
        if service_account_file:
            logger.info(f"Attempting to load credentials from: {service_account_file}")
            
            if os.path.exists(service_account_file):
                logger.info("Service account file exists, loading credentials...")
                credentials, project_id = load_credentials_from_file(service_account_file)
                vertexai.init(project=project_id, location=location, credentials=credentials)
                logger.info(f"Successfully loaded credentials from file for project: {project_id}")
            else:
                logger.error(f"Service account file not found at: {service_account_file}")
                logger.info("Falling back to application default credentials...")
                vertexai.init(project=project_id, location=location)
        else:
            logger.info("No GOOGLE_APPLICATION_CREDENTIALS environment variable set. Using application default credentials.")
            vertexai.init(project=project_id, location=location)
            
        logger.info("Vertex AI initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def initialize_genai_client():
    """
    Initialize the GenAI client with proper configuration.
    """
    global _genai_client
    
    try:
        # First initialize Vertex AI
        initialize_vertexai()
        
        # Set environment variables for GenAI
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_ID")
        location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GCP_LOCATION")
        
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT or GCP_ID environment variable is required")
        
        # Set environment variables for GenAI to use Vertex AI
        # Use us-central1 for better model availability
        effective_location = 'us-central1' if location == 'europe-west4' else location
        os.environ['GOOGLE_CLOUD_PROJECT'] = project_id
        os.environ['GOOGLE_CLOUD_LOCATION'] = effective_location
        os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = 'True'
        
        # Get credentials from Vertex AI initialization
        service_account_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        credentials = None
        
        if service_account_file and os.path.exists(service_account_file):
            credentials, _ = load_credentials_from_file(service_account_file)
        
        # Initialize the GenAI client with Vertex AI configuration
        _genai_client = genai.Client(
            vertexai=True,
            project=project_id,
            location=effective_location
        )
        
        logger.info(f"GenAI client initialized successfully for project {project_id} in {effective_location}")
        
    except Exception as e:
        logger.error(f"Failed to initialize GenAI client: {str(e)}")
        raise

def get_genai_client():
    """
    Get the initialized GenAI client.
    """
    global _genai_client
    
    if _genai_client is None:
        raise RuntimeError("GenAI client not initialized. Call initialize_genai_client() first.")
    
    return _genai_client

def is_client_initialized():
    """
    Check if the GenAI client has been initialized.
    """
    global _genai_client
    return _genai_client is not None
