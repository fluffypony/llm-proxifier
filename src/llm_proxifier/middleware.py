"""Authentication middleware for LLM Proxifier."""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from llm_proxifier.auth import (
    AuthManager,
    create_auth_error_response,
    create_permission_error_response,
    extract_bearer_token,
)

logger = logging.getLogger(__name__)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API key authentication and authorization."""

    def __init__(self, app, auth_manager: AuthManager = None):
        super().__init__(app)
        self.auth_manager = auth_manager

    def set_auth_manager(self, auth_manager: AuthManager):
        """Set the auth manager after initialization."""
        self.auth_manager = auth_manager

    async def dispatch(self, request: Request, call_next):
        """Process authentication for each request."""
        # Get auth_manager from app state if not set
        if self.auth_manager is None:
            self.auth_manager = getattr(request.app.state, 'auth_manager', None)

        # If auth_manager is still not available, skip authentication
        if self.auth_manager is None:
            return await call_next(request)

        # Skip auth for static files
        if request.url.path.startswith("/static/"):
            return await call_next(request)

        # Get the endpoint path
        endpoint = request.url.path

        # Check if authentication is required for this endpoint
        if not self.auth_manager.config_manager.auth_config.enabled:
            # Authentication disabled, continue normally
            return await call_next(request)

        # Check if endpoint is public (no auth required)
        if self.auth_manager.config_manager.auth_config.is_public_endpoint(endpoint):
            return await call_next(request)

        # Special handling for dashboard
        if endpoint.startswith("/dashboard"):
            if not self.auth_manager.is_dashboard_auth_required():
                return await call_next(request)

        # Extract API key from Authorization header
        authorization = request.headers.get("Authorization")
        api_key = extract_bearer_token(authorization)

        if not api_key:
            logger.warning(f"Missing API key for protected endpoint: {endpoint}")
            return JSONResponse(
                status_code=401,
                content=create_auth_error_response("Missing or invalid API key")
            )

        # Verify API key
        api_key_config = self.auth_manager.verify_api_key(api_key)
        if not api_key_config:
            logger.warning(f"Invalid API key for endpoint: {endpoint}")
            return JSONResponse(
                status_code=401,
                content=create_auth_error_response("Invalid or expired API key")
            )

        # Check permissions
        if not self.auth_manager.check_permission(api_key_config, endpoint):
            logger.warning(f"Permission denied for key '{api_key_config.name}' on endpoint: {endpoint}")
            return JSONResponse(
                status_code=403,
                content=create_permission_error_response(f"Key '{api_key_config.name}' does not have permission for {endpoint}")
            )

        # Add API key info to request state for downstream use
        request.state.api_key_config = api_key_config
        request.state.authenticated = True

        # Log successful authentication
        logger.debug(f"Authenticated request from key '{api_key_config.name}' for endpoint: {endpoint}")

        # Continue with the request
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to handle rate limiting per API key."""

    def __init__(self, app, auth_manager: AuthManager = None):
        super().__init__(app)
        self.auth_manager = auth_manager
        self.request_counts = {}  # Simple in-memory store - TODO: use Redis for production

    def set_auth_manager(self, auth_manager: AuthManager):
        """Set the auth manager after initialization."""
        self.auth_manager = auth_manager

    async def dispatch(self, request: Request, call_next):
        """Process rate limiting for each request."""
        # Get auth_manager from app state if not set
        if self.auth_manager is None:
            self.auth_manager = getattr(request.app.state, 'auth_manager', None)

        # If auth_manager is still not available, skip rate limiting
        if self.auth_manager is None:
            return await call_next(request)

        # Skip rate limiting for static files
        if request.url.path.startswith("/static/"):
            return await call_next(request)

        # Skip if auth is disabled
        if not self.auth_manager.config_manager.auth_config.enabled:
            return await call_next(request)

        # Get API key config from request state (set by auth middleware)
        api_key_config = getattr(request.state, 'api_key_config', None)

        # Determine rate limit
        rate_limit = self.auth_manager.get_rate_limit(api_key_config)

        # Simple rate limiting logic (requests per minute)
        # In production, this should use a proper rate limiting algorithm
        key = api_key_config.key if api_key_config else request.client.host

        # TODO: Implement proper sliding window rate limiting
        # For now, just log the rate limit that would be applied
        logger.debug(f"Rate limit for {key}: {rate_limit} requests/minute")

        return await call_next(request)


def create_auth_middleware(auth_manager: AuthManager):
    """Factory function to create authentication middleware."""
    return AuthenticationMiddleware, {"auth_manager": auth_manager}


def create_rate_limit_middleware(auth_manager: AuthManager):
    """Factory function to create rate limiting middleware."""
    return RateLimitMiddleware, {"auth_manager": auth_manager}
