"""Authentication module for LLM Proxifier."""

import os
import secrets
import hashlib
from typing import Optional, List
from datetime import datetime

from passlib.context import CryptContext
from src.config import ConfigManager, APIKeyConfig


class AuthManager:
    """Manages authentication and authorization."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
    def verify_api_key(self, api_key: str) -> Optional[APIKeyConfig]:
        """Verify an API key and return the associated configuration."""
        if not self.config_manager.auth_config.enabled:
            return None  # Auth disabled, no verification needed
            
        key_config = self.config_manager.auth_config.get_api_key(api_key)
        if not key_config:
            return None
            
        if key_config.is_expired():
            return None
            
        return key_config
    
    def check_permission(self, api_key_config: Optional[APIKeyConfig], endpoint: str) -> bool:
        """Check if API key has permission for endpoint."""
        if not self.config_manager.auth_config.enabled:
            return True  # Auth disabled, allow all
            
        # Check if endpoint is public
        if self.config_manager.auth_config.is_public_endpoint(endpoint):
            return True
            
        # If auth is required but no key provided
        if not api_key_config:
            return False
            
        return api_key_config.has_permission(endpoint)
    
    def is_dashboard_auth_required(self) -> bool:
        """Check if dashboard requires authentication."""
        return (self.config_manager.auth_config.enabled and 
                self.config_manager.auth_config.dashboard_auth_required)
    
    def generate_api_key(self) -> str:
        """Generate a new secure API key."""
        return secrets.token_urlsafe(32)
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for secure storage."""
        return self.pwd_context.hash(api_key)
    
    def verify_api_key_hash(self, api_key: str, hashed_key: str) -> bool:
        """Verify an API key against its hash."""
        return self.pwd_context.verify(api_key, hashed_key)
    
    def get_rate_limit(self, api_key_config: Optional[APIKeyConfig]) -> int:
        """Get rate limit for API key."""
        if not api_key_config:
            return self.config_manager.auth_config.rate_limits.get("default", 100)
            
        # Check if key name has specific rate limit
        key_name_lower = api_key_config.name.lower()
        for limit_name, limit_value in self.config_manager.auth_config.rate_limits.items():
            if limit_name in key_name_lower:
                return limit_value
                
        return self.config_manager.auth_config.rate_limits.get("default", 100)


def extract_bearer_token(authorization_header: Optional[str]) -> Optional[str]:
    """Extract bearer token from Authorization header."""
    if not authorization_header:
        return None
        
    if not authorization_header.startswith("Bearer "):
        return None
        
    return authorization_header[7:]  # Remove "Bearer " prefix


def create_auth_error_response(message: str = "Authentication required") -> dict:
    """Create standardized authentication error response."""
    return {
        "error": {
            "message": message,
            "type": "authentication_error",
            "code": 401
        }
    }


def create_permission_error_response(message: str = "Insufficient permissions") -> dict:
    """Create standardized permission error response."""
    return {
        "error": {
            "message": message,
            "type": "permission_error",
            "code": 403
        }
    }
