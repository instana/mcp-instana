"""
Tests for API headers authentication priority.
"""
import os
from unittest.mock import patch

import pytest

from src.core.api_headers import AuthenticationError, build_instana_api_headers


class TestBuildInstanaApiHeaders:
    """Test authentication priority in build_instana_api_headers."""

    def test_priority_1_session_token_over_api_token(self):
        """Test that session token (auth_token + csrf_token) takes priority over API token."""
        headers = build_instana_api_headers(
            auth_token="session_token_123",
            csrf_token="csrf_token_456",
            api_token="api_token_789",  # Both provided
            cookie_name="instanaAuthToken"
        )

        # Should use session token, not API token
        assert "X-CSRF-TOKEN" in headers
        assert "Cookie" in headers
        assert headers["X-CSRF-TOKEN"] == "csrf_token_456"
        assert "instanaAuthToken=session_token_123" in headers["Cookie"]
        assert "Authorization" not in headers  # API token NOT used

    def test_priority_2_jwt_token_over_api_token(self):
        """Test that JWT token with CSRF takes priority over API token."""
        headers = build_instana_api_headers(
            jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            csrf_token="csrf_token_123",
            api_token="api_token_789"  # Both provided
        )

        # Should use JWT token with CSRF, not API token
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert "X-CSRF-TOKEN" in headers
        assert headers["X-CSRF-TOKEN"] == "csrf_token_123"
        assert "Cookie" not in headers

    def test_priority_2_jwt_token_when_no_session_token(self):
        """Test that JWT token with CSRF is used when session token is not provided."""
        headers = build_instana_api_headers(
            jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            csrf_token="csrf_token_456"
        )

        # Should use JWT token with Bearer prefix and CSRF
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert "X-CSRF-TOKEN" in headers
        assert headers["X-CSRF-TOKEN"] == "csrf_token_456"
        assert "Cookie" not in headers

    def test_priority_3_api_token_when_no_session_or_jwt_token(self):
        """Test that API token is used when session token and JWT token are not provided."""
        headers = build_instana_api_headers(
            api_token="api_token_789"
        )

        # Should use API token
        assert "Authorization" in headers
        assert headers["Authorization"] == "apiToken api_token_789"
        assert "X-CSRF-TOKEN" not in headers
        assert "Cookie" not in headers

    def test_priority_3_api_token_when_partial_session_token(self):
        """Test that API token is used when only auth_token is provided (missing csrf_token)."""
        headers = build_instana_api_headers(
            auth_token="session_token_123",
            api_token="api_token_789"
        )

        # Should use API token because csrf_token is missing
        assert "Authorization" in headers
        assert headers["Authorization"] == "apiToken api_token_789"
        assert "X-CSRF-TOKEN" not in headers

    def test_jwt_token_requires_csrf(self):
        """Test that JWT token requires CSRF token."""
        with pytest.raises(ValueError, match="CSRF token must be provided for JWT authentication"):
            build_instana_api_headers(
                jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
                # Missing csrf_token
            )

    def test_jwt_token_with_csrf_when_partial_session_token(self):
        """Test that JWT token with CSRF is used when only auth_token is provided (missing full session)."""
        headers = build_instana_api_headers(
            auth_token="session_token_123",
            csrf_token="csrf_token_456",
            jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        )

        # Should use JWT token with CSRF because session is incomplete (no cookie_name)
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert "X-CSRF-TOKEN" in headers
        assert headers["X-CSRF-TOKEN"] == "csrf_token_456"

    @patch.dict(os.environ, {"INSTANA_API_TOKEN": "env_api_token_999"})
    def test_priority_4_environment_fallback(self):
        """Test that environment variable is used as fallback."""
        headers = build_instana_api_headers()

        # Should use environment variable
        assert "Authorization" in headers
        assert headers["Authorization"] == "apiToken env_api_token_999"

    @patch.dict(os.environ, {"INSTANA_API_TOKEN": "env_api_token_999"})
    def test_session_token_overrides_environment(self):
        """Test that session token takes priority over environment variable."""
        headers = build_instana_api_headers(
            auth_token="session_token_123",
            csrf_token="csrf_token_456",
            cookie_name="instanaAuthToken"
        )

        # Should use session token, not environment
        assert "X-CSRF-TOKEN" in headers
        assert "Cookie" in headers
        assert "Authorization" not in headers

    @patch.dict(os.environ, {"INSTANA_API_TOKEN": "env_api_token_999"})
    def test_jwt_token_overrides_environment(self):
        """Test that JWT token with CSRF takes priority over environment variable."""
        headers = build_instana_api_headers(
            jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            csrf_token="csrf_token_789"
        )

        # Should use JWT token with CSRF, not environment
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        assert "X-CSRF-TOKEN" in headers
        assert headers["X-CSRF-TOKEN"] == "csrf_token_789"

    @patch.dict(os.environ, {"INSTANA_API_TOKEN": "env_api_token_999"})
    def test_api_token_overrides_environment(self):
        """Test that explicit API token takes priority over environment variable."""
        headers = build_instana_api_headers(
            api_token="api_token_789"
        )

        # Should use explicit API token, not environment
        assert "Authorization" in headers
        assert headers["Authorization"] == "apiToken api_token_789"

    def test_custom_cookie_name(self):
        """Test that custom cookie name is used when provided."""
        headers = build_instana_api_headers(
            auth_token="session_token_123",
            csrf_token="csrf_token_456",
            cookie_name="custom-cookie"
        )

        assert "Cookie" in headers
        assert "custom-cookie=session_token_123" in headers["Cookie"]

    def test_missing_cookie_name_raises_error(self):
        """Test that missing cookie name raises ValueError."""
        with pytest.raises(ValueError, match="Cookie name must be provided"):
            build_instana_api_headers(
                auth_token="session_token_123",
                csrf_token="csrf_token_456"
            )

    @patch.dict(os.environ, {}, clear=True)
    def test_no_credentials_raises_authentication_error(self):
        """Test that AuthenticationError is raised when no credentials are provided."""
        with pytest.raises(AuthenticationError, match="No authentication credentials provided"):
            build_instana_api_headers()

    def test_only_csrf_token_no_auth(self):
        """Test that only csrf_token without auth_token doesn't trigger session auth."""
        headers = build_instana_api_headers(
            csrf_token="csrf_token_456",
            api_token="api_token_789"
        )

        # Should use API token because auth_token is missing
        assert "Authorization" in headers
        assert headers["Authorization"] == "apiToken api_token_789"
        assert "X-CSRF-TOKEN" not in headers

    def test_invalid_cookie_name_with_semicolon(self):
        """Test that cookie name with semicolon is rejected (cookie injection prevention)."""
        with pytest.raises(ValueError, match="Cookie name contains invalid characters"):
            build_instana_api_headers(
                auth_token="session_token_123",
                csrf_token="csrf_token_456",
                cookie_name="malicious;cookie=injected"
            )

    def test_invalid_cookie_name_with_equals(self):
        """Test that cookie name with equals sign is rejected (cookie injection prevention)."""
        with pytest.raises(ValueError, match="Cookie name contains invalid characters"):
            build_instana_api_headers(
                auth_token="session_token_123",
                csrf_token="csrf_token_456",
                cookie_name="malicious=value"
            )

    def test_invalid_cookie_name_with_spaces(self):
        """Test that cookie name with spaces is rejected."""
        with pytest.raises(ValueError, match="Cookie name contains invalid characters"):
            build_instana_api_headers(
                auth_token="session_token_123",
                csrf_token="csrf_token_456",
                cookie_name="invalid cookie name"
            )

    def test_valid_cookie_name_with_hyphen(self):
        """Test that cookie name with hyphens is accepted."""
        headers = build_instana_api_headers(
            auth_token="session_token_123",
            csrf_token="csrf_token_456",
            cookie_name="valid-cookie-name"
        )

        assert "Cookie" in headers
        assert "valid-cookie-name=session_token_123" in headers["Cookie"]

    def test_valid_cookie_name_with_underscore(self):
        """Test that cookie name with underscores is accepted."""
        headers = build_instana_api_headers(
            auth_token="session_token_123",
            csrf_token="csrf_token_456",
            cookie_name="valid_cookie_name"
        )

        assert "Cookie" in headers
        assert "valid_cookie_name=session_token_123" in headers["Cookie"]

    def test_api_token_exceeds_max_length(self):
        """Test that API token exceeding maximum length is rejected."""
        long_token = "a" * 2049  # Exceeds MAX_TOKEN_LENGTH of 2048
        with pytest.raises(ValueError, match="API token exceeds maximum length"):
            build_instana_api_headers(api_token=long_token)

    def test_session_auth_token_exceeds_max_length(self):
        """Test that session auth token exceeding maximum length is rejected."""
        long_token = "a" * 2049  # Exceeds MAX_TOKEN_LENGTH of 2048
        with pytest.raises(ValueError, match="Session auth token exceeds maximum length"):
            build_instana_api_headers(
                auth_token=long_token,
                csrf_token="valid_csrf_token",
                cookie_name="testCookie"
            )

    def test_csrf_token_exceeds_max_length(self):
        """Test that CSRF token exceeding maximum length is rejected."""
        long_token = "a" * 2049  # Exceeds MAX_TOKEN_LENGTH of 2048
        with pytest.raises(ValueError, match="CSRF token exceeds maximum length"):
            build_instana_api_headers(
                auth_token="valid_auth_token",
                csrf_token=long_token,
                cookie_name="testCookie"
            )

    @patch.dict(os.environ, {"INSTANA_API_TOKEN": "a" * 2049})
    def test_environment_token_exceeds_max_length(self):
        """Test that environment API token exceeding maximum length is rejected."""
        with pytest.raises(ValueError, match="Environment API token exceeds maximum length"):
            build_instana_api_headers()

    def test_api_token_at_max_length(self):
        """Test that API token at exactly maximum length is accepted."""
        max_length_token = "a" * 2048  # Exactly MAX_TOKEN_LENGTH
        headers = build_instana_api_headers(api_token=max_length_token)

        assert "Authorization" in headers
        assert headers["Authorization"] == f"apiToken {max_length_token}"

    def test_jwt_token_exceeds_max_length(self):
        """Test that JWT token exceeding maximum length is rejected."""
        long_token = "a" * 2049  # Exceeds MAX_TOKEN_LENGTH of 2048
        with pytest.raises(ValueError, match="JWT token exceeds maximum length"):
            build_instana_api_headers(
                jwt_token=long_token,
                csrf_token="valid_csrf"
            )

    def test_jwt_token_at_max_length(self):
        """Test that JWT token at exactly maximum length is accepted."""
        max_length_token = "a" * 2048  # Exactly MAX_TOKEN_LENGTH
        headers = build_instana_api_headers(
            jwt_token=max_length_token,
            csrf_token="valid_csrf"
        )

        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {max_length_token}"
        assert "X-CSRF-TOKEN" in headers

    def test_session_token_priority_over_jwt_token(self):
        """Test that session token takes priority over JWT token."""
        headers = build_instana_api_headers(
            auth_token="session_token_123",
            csrf_token="csrf_token_456",
            jwt_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test",
            cookie_name="instanaAuthToken"
        )

        # Should use session token, not JWT token
        assert "X-CSRF-TOKEN" in headers
        assert "Cookie" in headers
        assert headers["X-CSRF-TOKEN"] == "csrf_token_456"
        assert "instanaAuthToken=session_token_123" in headers["Cookie"]
        assert "Authorization" not in headers  # JWT token NOT used

    def test_jwt_token_format(self):
        """Test that JWT token uses Bearer prefix format and includes CSRF."""
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.test"
        headers = build_instana_api_headers(
            jwt_token=jwt_token,
            csrf_token="csrf_token_123"
        )

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")
        assert headers["Authorization"] == f"Bearer {jwt_token}"
        assert "X-CSRF-TOKEN" in headers
        assert headers["X-CSRF-TOKEN"] == "csrf_token_123"

    def test_api_token_format(self):
        """Test that API token uses apiToken prefix format."""
        api_token = "test_api_token_123"
        headers = build_instana_api_headers(api_token=api_token)

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("apiToken ")
        assert headers["Authorization"] == f"apiToken {api_token}"
