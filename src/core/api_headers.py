"""
Utility functions for building headers for Instana API invocation.
Adapted from kubernetes-agent for MCP server use.
"""
import logging
import os
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Maximum allowed length for authentication tokens
MAX_TOKEN_LENGTH = 2048

class AuthenticationError(Exception):
    """Raised when no valid authentication credentials are provided."""
    pass

def _validate_token_length(token: str, token_type: str) -> None:
    """
    Validate that token length is within reasonable limits.
    
    Prevents potential attacks with excessively long tokens that could
    cause memory issues or be used to inject malicious code.
    
    Args:
        token: The token to validate
        token_type: Description of the token type (for error messages)
        
    Raises:
        ValueError: If token exceeds maximum length
    """
    if len(token) > MAX_TOKEN_LENGTH:
        logger.error(f"{token_type} exceeds maximum length: {len(token)} > {MAX_TOKEN_LENGTH}")
        raise ValueError(f"{token_type} exceeds maximum length of {MAX_TOKEN_LENGTH}")

def _validate_cookie_name(name: str) -> bool:
    """
    Validate cookie name contains only safe characters.
    
    Prevents cookie injection attacks by ensuring the cookie name
    only contains alphanumeric characters, hyphens, and underscores.
    
    Args:
        name: The cookie name to validate
        
    Returns:
        True if the cookie name is valid, False otherwise
    """
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', name))

def build_instana_api_headers(
    auth_token: Optional[str] = None,
    csrf_token: Optional[str] = None,
    jwt_token: Optional[str] = None,
    api_token: Optional[str] = None,
    cookie_name: Optional[str] = None
) -> Dict[str, str]:
    """
    Build headers for Instana API invocation.

    Supports four authentication modes with the following priority:
    1. Session Token mode (Priority 1): When auth_token and csrf_token are provided (for UI calls via coordinator)
    2. JWT Token mode (Priority 2): When jwt_token is provided (for platform integration with Bearer token)
    3. API Token mode (Priority 3): When api_token is provided (for direct API calls)
    4. Environment fallback (Priority 4): Uses INSTANA_API_TOKEN environment variable

    Args:
        auth_token: The authentication token (for cookie-based auth from UI)
        csrf_token: The CSRF token (for cookie-based auth from UI)
        jwt_token: The JWT token (for Bearer token auth from platform/coordinator)
        api_token: The API token (for token-based auth)
        cookie_name: The cookie name for cookie-based auth (required for session-based authentication)

    Returns:
        Dictionary containing the headers needed for Instana API calls
        
    Raises:
        ValueError: If cookie_name is not provided for session-based authentication
        ValueError: If cookie_name contains invalid characters
        ValueError: If any token exceeds maximum length (2048 characters)
        AuthenticationError: If no valid authentication credentials are provided
    """
    # Check if user is trying to use session auth but missing cookie_name
    if auth_token and csrf_token and not cookie_name and not jwt_token:
        logger.error("Cookie name is required for session-based authentication")
        raise ValueError("Cookie name must be provided for session-based authentication")
    
    # Priority 1: Use session token (auth_token, csrf_token, and cookie_name) if all provided (UI mode via coordinator)
    if auth_token and csrf_token and cookie_name:
        logger.debug("Authentication method selected: session-based")
        
        # Validate token lengths
        _validate_token_length(auth_token, "Session auth token")
        _validate_token_length(csrf_token, "CSRF token")
        
        # Validate cookie name to prevent cookie injection attacks
        if not _validate_cookie_name(cookie_name):
            logger.error(f"Invalid cookie name format: {cookie_name}")
            raise ValueError(f"Cookie name contains invalid characters. Only alphanumeric, hyphens, and underscores are allowed.")
        
        # Build the headers
        headers = {
            "X-CSRF-TOKEN": csrf_token,
            "Cookie": f"{cookie_name}={auth_token}"
        }
        return headers

    # Priority 2: Use JWT token with CSRF (JWT auth is treated like UI user, requires CSRF for modifying operations)
    # Note: JWT authentication takes priority over API token when both auth_token+csrf_token are provided without cookie_name
    if jwt_token:
        logger.debug("Authentication method selected: jwt-token")
        
        # Validate token length
        _validate_token_length(jwt_token, "JWT token")
        
        # CSRF token is REQUIRED for JWT authentication (treated as UI user for POST/PUT/DELETE)
        if csrf_token is None:
            logger.error("CSRF token is required for JWT authentication")
            raise ValueError("CSRF token must be provided for JWT authentication (required for POST/PUT/DELETE operations)")
        
        _validate_token_length(csrf_token, "CSRF token")
        
        # Build the headers with both Bearer token and CSRF
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "X-CSRF-TOKEN": csrf_token
        }
        # Log masked tokens for debugging
        masked_jwt = f"{jwt_token[:20]}...{jwt_token[-10:]}" if len(jwt_token) > 30 else jwt_token[:10] + "..."
        masked_csrf = f"{csrf_token[:10]}...{csrf_token[-5:]}" if len(csrf_token) > 15 else csrf_token[:5] + "..."
        logger.debug(f"Built JWT auth headers - Authorization: Bearer {masked_jwt}, X-CSRF-TOKEN: {masked_csrf}")
        return headers
    
    # Priority 3: Use API token if provided (direct API mode)
    if api_token:
        logger.debug("Authentication method selected: api-token")
        
        # Validate token length
        _validate_token_length(api_token, "API token")
        
        headers = {
            "Authorization": f"apiToken {api_token}"
        }
        return headers

    # Priority 3: Environment fallback - use environment variable
    api_token_env = os.getenv("INSTANA_API_TOKEN")
    if api_token_env:
        logger.debug("Authentication method selected: environment-fallback")
        
        # Validate token length
        _validate_token_length(api_token_env, "Environment API token")
        
        headers = {
            "Authorization": f"apiToken {api_token_env}"
        }
        return headers
        
    # No valid authentication provided
    logger.error("No valid authentication credentials provided")
    raise AuthenticationError(
        "No authentication credentials provided. Please provide either:\n"
        "1. auth_token and csrf_token for session-based auth\n"
        "2. jwt_token for JWT Bearer token auth\n"
        "3. api_token for API token auth\n"
        "4. Set INSTANA_API_TOKEN environment variable"
    )
