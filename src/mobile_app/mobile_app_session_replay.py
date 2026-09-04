"""
Mobile App Session Replay MCP Tools Module

This module provides mobile app session replay-specific MCP tools for Instana monitoring.
"""

import json
import logging
from typing import Any, Dict, Optional

from fastmcp import Context

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 1000

def clean_nan_values(data: Any) -> Any:
    """
    Recursively replace string ``"NaN"`` values with ``None``.

    Some Instana API responses may contain the literal string ``"NaN"``
    instead of a null value. This helper normalizes nested dictionaries
    and lists so the returned payload is easier to consume.
    """
    if isinstance(data, dict):
        return {key: clean_nan_values(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, str) and data == 'NaN':
        return None
    else:
        return data

try:
    from instana_client.api.mobile_app_session_replay_api import (
        MobileAppSessionReplayApi,
    )
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    sdk_call_with_keepalive,
    with_header_auth,
)
from src.core.validation import ValidationError, ValidationResult

logger = logging.getLogger(__name__)

class MobileAppSessionReplayMCPTools(BaseInstanaClient):
    """Tools for mobile app session replay in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Mobile App Session Replay MCP Tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    def _validate_action_beacon_pagination_params(
        self,
        cursor: Optional[int] = None,
        page_size: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate pagination parameters for get_session_replay_action_beacons.

        Args:
            cursor: Zero-based beacon index to start reading from. Must be
                greater than or equal to 0 when provided.
            page_size: Maximum number of beacons to request in one call.
                Must be between 1 and 1000 when provided.

        Returns:
            A validation error dictionary when an input is invalid, otherwise
            ``None``.
        """
        validation = ValidationResult()

        if cursor is not None and cursor < 0:
            validation.add_error(
                ValidationError(
                    field="cursor",
                    message="cursor must be a non-negative integer",
                    provided_value=cursor,
                    valid_range="Must be >= 0",
                    example="10",
                )
            )

        if page_size is not None and (page_size < MIN_PAGE_SIZE or page_size > MAX_PAGE_SIZE):
            validation.add_error(
                ValidationError(
                    field="page_size",
                    message="page_size must be a positive integer",
                    provided_value=page_size,
                    valid_range="Must be 1 <= page_size <= 1000",
                    example="300",
                )
            )

        if not validation.is_valid():
            return {
                "validation_failed": True,
                **validation.to_dict(),
            }

        return None

    def _check_elicitation_for_action_beacon_required_params(
        self,
        mobile_app_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Build an elicitation response when required identifiers are missing.

        Args:
            mobile_app_id: The target mobile app ID, if already known.
            session_id: The target session ID, if already known.

        Returns:
            An elicitation dictionary describing the missing parameters, or
            ``None`` when all required identifiers are present.
        """

        missing_params = []

        if not mobile_app_id:
            missing_params.append({
                "name": "mobile_app_id",
                "description": "Target app id provided by user (REQUIRED)",
                "examples": ["i1IsNS7FQAegEljBTkNBMQ", "vpNGsUnMTd-0cccoxAw09g", "IyVaOWSXTLyMAchWaJq5wA"]
            })

        if not session_id:
            missing_params.append({
                "name": "session_id",
                "description": "Target app session provided by user (REQUIRED)",
                "examples": ["bffe55e0-4c78-4366-a5e2-be008113e37e", "1db2199a-27f8-4d09-9e5c-b50685369258", "1d616527-2635-407f-89fc-de7136b66fb4"]
            })

        if missing_params:
            return {
                "elicitation_needed": True,
                "missing_parameters": missing_params,
                "message": "Please provide the required parameters to get mobile app session replay action beacons",
                "elicitation_prompt": "To retrieve mobile app session replay action beacons, I need:\n" +
                 "\n".join([f"- {p['name']}: {p['description']}" for p in missing_params])
            }

        return None

    async def _execute_action_beacons_call(
        self,
        mobile_app_id: Optional[str] = None,
        session_id: Optional[str] = None,
        cursor: Optional[int] = None,
        page_size: Optional[int] = None,
        api_client = None,
        ctx = None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call the session replay action-beacons endpoint directly.

        Args:
            mobile_app_id: The mobile app ID for the session being queried.
            session_id: The session ID whose action beacons should be fetched.
            cursor: Zero-based beacon index to start reading from.
            page_size: Maximum number of beacons to request.
            ctx: The MCP context (optional)

        Returns:
            A dictionary containing the raw endpoint response on success, or
            an error dictionary when the HTTP request fails.
        """

        try:
            # Use without_preload_content to bypass Pydantic validation
            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_action_beacons_without_preload_content,
                    mobile_app_id=mobile_app_id,
                    session_id=session_id,
                    cursor=cursor,
                    page_size=page_size,
                ),
                ctx=ctx,
                operation_name="get_action_beacons",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            # Check if the response was successful
            if response.status != 200:
                return self.handle_api_error_response(response, "get mobile app session replay action beacons", logger)

            # Read and parse the response content
            response_text = decode_response(response)
            full_response = json.loads(response_text)

            return full_response
        except Exception as e:
            logger.error(f"[get_session_replay_action_beacons] Error: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app session beacons: {e!s}"}


    @with_header_auth(MobileAppSessionReplayApi)
    async def get_session_replay_action_beacons(
        self,
        mobile_app_id: Optional[str] = None,
        session_id: Optional[str] = None,
        cursor: Optional[int] = None,
        page_size: Optional[int] = None,
        ctx: Optional[Context] = None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve a page of session replay action beacons for a session.

        This method validates required identifiers and pagination inputs,
        applies defaults, calls the session replay endpoint, and returns the
        normalized response payload.

        Args:
            mobile_app_id: The mobile app ID that owns the session.
            session_id: The session ID to retrieve action beacons for.
            cursor: Zero-based beacon index to start reading from. Defaults
                to the beginning of the session when omitted.
            page_size: Maximum number of beacons to return in this request.

        Returns:
            A dictionary containing the requested page of action beacons, an
            elicitation response for missing required parameters, or a
            validation/error response if the request cannot be completed.
        """

        try:
            logger.debug(
                f"[get_session_replay_action_beacons] Called with mobile_app_id={mobile_app_id}, session_id={session_id}, "
                f"cursor={cursor}, page_size={page_size}"
            )

            # STEP 1: Check required parameters
            elicitation = self._check_elicitation_for_action_beacon_required_params(mobile_app_id, session_id)

            if elicitation:
                return elicitation

            # STEP 2: Validate pagination parameters
            validation = self._validate_action_beacon_pagination_params(cursor, page_size)

            if validation:
                return validation

            # STEP 3: Apply pagination parameter defaults
            if cursor is None:
                cursor = 0 # Set cursor to 0 to start at first beacon by default
                logger.debug("[get_session_replay_action_beacons] Default cursor applied since cursor not provided")

            if page_size is None:
                page_size = 100 # Set page_size to 100 by default
                logger.debug("[get_session_replay_action_beacons] Default page_size applied since page_size not provided")

            #STEP 4: Pull beacons
            response = await self._execute_action_beacons_call(mobile_app_id, session_id, cursor, page_size, api_client, ctx=ctx, resource_type=resource_type, tool_name=tool_name)

            if "error" in response:
                logger.debug(
                    f"[get_session_replay_action_beacons] Failed call to action-beacons endpoint with mobile_app_id={mobile_app_id},"
                    f"session_id={session_id}, cursor={cursor}, page_size={page_size}"
                )
                return response

            beacons = response.get("beacons", [])
            if not beacons:
                logger.debug(
                    "[get_session_replay_action_beacons] Empty beacons list returned by endpoint, possible invalid mobile_app_id or session_id or session may be empty. "
                    f"Endpoint called with mobile_app_id={mobile_app_id}, session_id={session_id}, cursor={cursor}, page_size={page_size}"
                )

            return clean_nan_values(response)

        except Exception as e:
            logger.error(f"[get_session_replay_action_beacons] Error: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app replay action beacons: {e!s}"}
