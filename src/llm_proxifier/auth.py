"""Authentication module for LLM Proxifier."""

import secrets
from datetime import datetime
from typing import Any, Dict, Optional

from passlib.context import CryptContext

from llm_proxifier.config import APIKeyConfig, ConfigManager


class AuthManager:
    """Manages authentication and authorization."""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._api_key_cache = None
        self._last_config_update = None

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

    def update_config(self, config_manager: ConfigManager) -> Dict[str, Any]:
        """Update authentication configuration with new ConfigManager."""
        import logging
        logger = logging.getLogger(__name__)

        old_config = self.config_manager
        new_config = config_manager

        # Track changes
        changes = {
            "enabled_changed": old_config.auth_config.enabled != new_config.auth_config.enabled,
            "api_keys_changed": False,
            "rate_limits_changed": False,
            "dashboard_auth_changed": old_config.auth_config.dashboard_auth_required != new_config.auth_config.dashboard_auth_required,
            "public_endpoints_changed": False
        }

        # Check API keys changes
        old_keys = set(old_config.auth_config.api_keys.keys()) if old_config.auth_config.api_keys else set()
        new_keys = set(new_config.auth_config.api_keys.keys()) if new_config.auth_config.api_keys else set()
        changes["api_keys_changed"] = old_keys != new_keys

        # Check rate limits changes
        old_limits = old_config.auth_config.rate_limits or {}
        new_limits = new_config.auth_config.rate_limits or {}
        changes["rate_limits_changed"] = old_limits != new_limits

        # Check public endpoints changes
        old_endpoints = set(old_config.auth_config.public_endpoints or [])
        new_endpoints = set(new_config.auth_config.public_endpoints or [])
        changes["public_endpoints_changed"] = old_endpoints != new_endpoints

        # Update the config manager
        self.config_manager = new_config

        # Clear caches
        self._api_key_cache = None
        self._last_config_update = datetime.now()

        # Log changes
        if any(changes.values()):
            logger.info(f"Authentication configuration updated: {changes}")
        else:
            logger.info("Authentication configuration reloaded (no changes)")

        return {
            "success": True,
            "changes": changes,
            "updated_at": self._last_config_update.isoformat()
        }

    def reload_api_keys(self) -> Dict[str, Any]:
        """Refresh the in-memory API key cache."""
        import logging
        logger = logging.getLogger(__name__)

        old_cache_size = len(self._api_key_cache) if self._api_key_cache else 0

        # Clear the cache to force reload from config
        self._api_key_cache = None

        # Get current API keys count
        current_keys = self.config_manager.auth_config.api_keys or {}
        new_cache_size = len(current_keys)

        logger.info(f"API keys cache reloaded: {old_cache_size} -> {new_cache_size} keys")

        return {
            "success": True,
            "old_count": old_cache_size,
            "new_count": new_cache_size,
            "reloaded_at": datetime.now().isoformat()
        }

    def validate_new_config(self, auth_config) -> Dict[str, Any]:
        """Validate authentication configuration before applying."""
        import logging
        logger = logging.getLogger(__name__)

        errors = []
        warnings = []

        # Validate required fields
        if not hasattr(auth_config, 'enabled'):
            errors.append("Missing 'enabled' field")

        # Validate API keys if auth is enabled
        if hasattr(auth_config, 'enabled') and auth_config.enabled:
            if not hasattr(auth_config, 'api_keys') or not auth_config.api_keys:
                warnings.append("Authentication enabled but no API keys configured")
            else:
                # Validate each API key
                for key_name, key_config in auth_config.api_keys.items():
                    if not hasattr(key_config, 'key'):
                        errors.append(f"API key '{key_name}' missing 'key' field")
                    if not hasattr(key_config, 'permissions'):
                        errors.append(f"API key '{key_name}' missing 'permissions' field")

        # Validate rate limits
        if hasattr(auth_config, 'rate_limits') and auth_config.rate_limits:
            for limit_name, limit_value in auth_config.rate_limits.items():
                if not isinstance(limit_value, int) or limit_value <= 0:
                    errors.append(f"Rate limit '{limit_name}' must be a positive integer")

        # Validate public endpoints
        if hasattr(auth_config, 'public_endpoints') and auth_config.public_endpoints:
            if not isinstance(auth_config.public_endpoints, list):
                errors.append("Public endpoints must be a list")

        is_valid = len(errors) == 0

        if errors:
            logger.error(f"Authentication config validation failed: {errors}")
        if warnings:
            logger.warning(f"Authentication config validation warnings: {warnings}")

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "validated_at": datetime.now().isoformat()
        }


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
