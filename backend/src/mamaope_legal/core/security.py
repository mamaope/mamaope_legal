"""
Security utilities for mamaope_legal AI CDSS.

This module provides secure authentication, encryption, and data protection
utilities following medical software security standards (HIPAA/GDPR/ISO 13485).
"""

import os
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Security configuration constants."""
    
    # Encryption settings
    ENCRYPTION_KEY_LENGTH = 32
    SALT_LENGTH = 16
    
    # Token settings
    ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Reduced from 60 for better security
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Password settings
    MIN_PASSWORD_LENGTH = 12
    MAX_PASSWORD_LENGTH = 128
    PASSWORD_REQUIREMENTS = {
        'min_length': MIN_PASSWORD_LENGTH,
        'max_length': MAX_PASSWORD_LENGTH,
        'require_uppercase': True,
        'require_lowercase': True,
        'require_digits': True,
        'require_special_chars': True,
        'forbidden_patterns': ['password', '123456', 'qwerty', 'admin']
    }
    
    # Rate limiting
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15
    
    # Input validation
    MAX_PATIENT_DATA_LENGTH = 10000  # 10KB limit for patient data
    MAX_CHAT_HISTORY_LENGTH = 50000  # 50KB limit for chat history
    MAX_QUERY_LENGTH = 2000


class EncryptionService:
    """Service for encrypting/decrypting sensitive medical data."""
    
    def __init__(self):
        self._key = self._get_or_create_encryption_key()
        self._fernet = Fernet(self._key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key from environment."""
        key_str = os.getenv('ENCRYPTION_KEY')
        if not key_str:
            logger.warning("ENCRYPTION_KEY not found in environment. Generating new key.")
            key = Fernet.generate_key()
            logger.critical(f"Generated new encryption key: {key.decode()}")
            logger.critical("IMPORTANT: Save this key securely and set ENCRYPTION_KEY environment variable!")
            return key
        
        try:
            # Try to decode as base64 first
            decoded_key = base64.urlsafe_b64decode(key_str.encode())
            if len(decoded_key) == 32:
                return decoded_key
            else:
                raise ValueError("Invalid key length")
        except Exception:
            try:
                # If that fails, generate a new key
                logger.warning("Invalid ENCRYPTION_KEY format. Generating new key.")
                key = Fernet.generate_key()
                logger.critical(f"Generated new encryption key: {key.decode()}")
                logger.critical("IMPORTANT: Save this key securely and set ENCRYPTION_KEY environment variable!")
                return key
            except Exception as e:
                logger.error(f"Failed to generate encryption key: {e}")
                # Last resort - generate a key
                return Fernet.generate_key()
    
    def encrypt_phi(self, data: str) -> str:
        """
        Encrypt PHI (Protected Health Information) data.
        
        Args:
            data: Plain text PHI data to encrypt
            
        Returns:
            Base64 encoded encrypted data
            
        Raises:
            ValueError: If data is too large or invalid
        """
        if not isinstance(data, str):
            raise ValueError("Data must be a string")
        
        if len(data.encode('utf-8')) > SecurityConfig.MAX_PATIENT_DATA_LENGTH:
            raise ValueError(f"Data too large. Max size: {SecurityConfig.MAX_PATIENT_DATA_LENGTH} bytes")
        
        try:
            encrypted_data = self._fernet.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Encryption failed")
    
    def decrypt_phi(self, encrypted_data: str) -> str:
        """
        Decrypt PHI data.
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted plain text data
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            decoded_data = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self._fernet.decrypt(decoded_data)
            return decrypted_data.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed")


class PasswordValidator:
    """Validates password strength according to medical software standards."""
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Dict with validation results
        """
        requirements = SecurityConfig.PASSWORD_REQUIREMENTS
        errors = []
        warnings = []
        
        # Length validation
        if len(password) < requirements['min_length']:
            errors.append(f"Password must be at least {requirements['min_length']} characters")
        if len(password) > requirements['max_length']:
            errors.append(f"Password must be no more than {requirements['max_length']} characters")
        
        # Character requirements
        if requirements['require_uppercase'] and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if requirements['require_lowercase'] and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if requirements['require_digits'] and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if requirements['require_special_chars']:
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                errors.append("Password must contain at least one special character")
        
        # Forbidden patterns
        password_lower = password.lower()
        for pattern in requirements['forbidden_patterns']:
            if pattern in password_lower:
                errors.append(f"Password cannot contain '{pattern}'")
        
        # Additional security checks
        if password.count(password[0]) > len(password) * 0.5:
            warnings.append("Password has too many repeated characters")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'strength_score': PasswordValidator._calculate_strength_score(password)
        }
    
    @staticmethod
    def _calculate_strength_score(password: str) -> int:
        """Calculate password strength score (0-100)."""
        score = 0
        
        # Length score
        score += min(len(password) * 2, 40)
        
        # Character variety
        if any(c.isupper() for c in password):
            score += 10
        if any(c.islower() for c in password):
            score += 10
        if any(c.isdigit() for c in password):
            score += 10
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 10
        
        # Complexity bonus
        unique_chars = len(set(password))
        score += min(unique_chars * 2, 20)
        
        return min(score, 100)


class SecureLogger:
    """Secure logging utility that prevents PHI leakage."""
    
    # Patterns that might indicate PHI
    PHI_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b',  # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}-\d{3}-\d{4}\b',  # Phone
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # Date
        r'\b(?:Mr|Mrs|Ms|Dr)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Name with title
    ]
    
    @staticmethod
    def sanitize_log_message(message: str) -> str:
        """
        Sanitize log message to remove potential PHI.
        
        Args:
            message: Log message to sanitize
            
        Returns:
            Sanitized message with PHI replaced by [REDACTED]
        """
        import re
        
        sanitized = message
        for pattern in SecureLogger.PHI_PATTERNS:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @staticmethod
    def log_securely(level: str, message: str, **kwargs):
        """
        Log message with PHI sanitization.
        
        Args:
            level: Log level (info, warning, error, etc.)
            message: Log message
            **kwargs: Additional logging parameters
        """
        sanitized_message = SecureLogger.sanitize_log_message(message)
        
        if level.lower() == 'info':
            logger.info(sanitized_message, **kwargs)
        elif level.lower() == 'warning':
            logger.warning(sanitized_message, **kwargs)
        elif level.lower() == 'error':
            logger.error(sanitized_message, **kwargs)
        elif level.lower() == 'critical':
            logger.critical(sanitized_message, **kwargs)
        else:
            logger.debug(sanitized_message, **kwargs)

    def log_request(self, action: str, details: Dict[str, Any]):
        """
        Log a request action with PHI sanitization.

        Args:
            action: The action being logged (e.g., 'generate_response', 'generate_response_success')
            details: Dictionary of details to log
        """
        message = f"Action: {action}, Details: {details}"
        SecureLogger.log_securely('info', message)


class InputValidator:
    """Validates and sanitizes user inputs."""
    
    @staticmethod
    def validate_patient_data(data: str) -> Dict[str, Any]:
        """
        Validate patient data input.
        
        Args:
            data: Patient data string to validate
            
        Returns:
            Validation result dict
        """
        if not isinstance(data, str):
            return {'is_valid': False, 'error': 'Patient data must be a string'}
        
        if len(data.strip()) == 0:
            return {'is_valid': False, 'error': 'Patient data cannot be empty'}
        
        if len(data) > SecurityConfig.MAX_PATIENT_DATA_LENGTH:
            return {
                'is_valid': False, 
                'error': f'Patient data too long. Max length: {SecurityConfig.MAX_PATIENT_DATA_LENGTH} characters'
            }
        
        # Check for potentially malicious content
        dangerous_patterns = [
            r'<script.*?>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript protocol
            r'data:text/html',  # Data URLs
            r'vbscript:',  # VBScript
        ]
        
        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                return {'is_valid': False, 'error': 'Invalid content detected'}
        
        return {'is_valid': True, 'sanitized_data': InputValidator._sanitize_text(data)}
    
    @staticmethod
    def validate_chat_history(history: str) -> Dict[str, Any]:
        """Validate chat history input."""
        if not isinstance(history, str):
            return {'is_valid': False, 'error': 'Chat history must be a string'}
        
        if len(history) > SecurityConfig.MAX_CHAT_HISTORY_LENGTH:
            return {
                'is_valid': False,
                'error': f'Chat history too long. Max length: {SecurityConfig.MAX_CHAT_HISTORY_LENGTH} characters'
            }
        
        return {'is_valid': True, 'sanitized_data': InputValidator._sanitize_text(history)}

    @staticmethod
    def validate_query(query: str) -> str:
        """Validate and sanitize query input."""
        if not isinstance(query, str):
            query = str(query)

        # Basic validation - ensure it's not empty and not too long
        if len(query.strip()) == 0:
            return ""

        if len(query) > 2000:  # Reasonable limit for queries
            query = query[:2000]

        return InputValidator._sanitize_text(query)

    @staticmethod
    def validate_context(context: str) -> str:
        """Validate and sanitize context input."""
        if not isinstance(context, str):
            context = str(context)

        # Basic validation - ensure it's not empty and not too long
        if len(context.strip()) == 0:
            return ""

        if len(context) > 50000:  # Reasonable limit for context
            context = context[:50000]

        return InputValidator._sanitize_text(context)

    @staticmethod
    def validate_sources(sources: str) -> str:
        """Validate and sanitize sources input."""
        if not isinstance(sources, str):
            sources = str(sources)

        # Basic validation - ensure it's not empty and not too long
        if len(sources.strip()) == 0:
            return "General medical knowledge"

        if len(sources) > 1000:  # Reasonable limit for sources
            sources = sources[:1000]

        return InputValidator._sanitize_text(sources)

    @staticmethod
    def validate_response(response: str) -> str:
        """Validate and sanitize response input."""
        if not isinstance(response, str):
            response = str(response)

        # Basic validation - ensure it's not empty and not too long
        if len(response.strip()) == 0:
            return ""

        if len(response) > 10000:  # Reasonable limit for responses
            response = response[:10000]

        return InputValidator._sanitize_text(response)

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Basic text sanitization."""
        import html
        
        # HTML escape
        sanitized = html.escape(text)
        
        # Remove excessive whitespace
        sanitized = ' '.join(sanitized.split())
        
        return sanitized


def generate_secure_secret_key() -> str:
    """Generate a cryptographically secure secret key."""
    return secrets.token_urlsafe(32)


def verify_environment_security() -> Dict[str, bool]:
    """
    Verify that environment is properly configured for security.
    
    Returns:
        Dict with security check results
    """
    checks = {
        'secret_key_configured': bool(os.getenv('SECRET_KEY')) and os.getenv('SECRET_KEY') != 'supersecretkey',
        'encryption_key_configured': bool(os.getenv('ENCRYPTION_KEY')),
        'database_password_secure': os.getenv('DB_PASSWORD') != 'password',
        'cors_restricted': os.getenv('CORS_ORIGINS') != '*',
        'environment_production': os.getenv('ENV') == 'production',
    }
    
    return checks
