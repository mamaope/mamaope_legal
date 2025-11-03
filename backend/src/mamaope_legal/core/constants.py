"""
Application constants for mamaope_legal AI CDSS.
"""

# Model Configuration
MODEL_NAME = "gemini-2.5-flash"
PROMPT_TOKEN_LIMIT = 16000

# Cache Configuration
CACHE_TTL_MINUTES = 30  # Cache responses for 30 minutes
MAX_CACHE_SIZE = 100  # Maximum number of cached responses

# Context Optimization
DEFAULT_CONTEXT_MAX_CHARS = 1200  # Default context length for optimization
BALANCED_CONTEXT_MAX_CHARS = 1800  # Balanced context length for quality

# Streaming Configuration
CHUNK_SIZE = 50  # Size of chunks for streaming cached responses
STREAM_DELAY = 0.01  # Delay between streaming chunks in seconds

# Retry Configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_MULTIPLIER = 1
RETRY_MIN_WAIT = 4
RETRY_MAX_WAIT = 10
