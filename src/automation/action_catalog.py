"""
Automation Action Catalog MCP Tools Module

This module provides automation action catalog tools for Instana Automation.
"""

import ast
import json
import logging
from typing import Any, Dict, List, Optional, Union

# Import the necessary classes from the SDK
try:
    from instana_client.api.action_catalog_api import (
        ActionCatalogApi,
    )
except ImportError:
    logging.getLogger(__name__).error("Failed to import Action Catalog API", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    register_as_tool,
    sdk_call_with_keepalive,
    with_header_auth,
)

# Configure logger for this module
logger = logging.getLogger(__name__)

class ActionCatalogMCPTools(BaseInstanaClient):
    """Tools for application alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @staticmethod
    def _parse_action_matches_payload(
        payload: Union[Dict[str, Any], str],
    ) -> Union[Dict[str, Any], tuple]:
        """
        Parse and validate the raw payload for get_action_matches.

        Returns the parsed dict on success, or a (elicitation_dict,) 1-tuple on failure
        so callers can distinguish a parse error from a valid empty dict.
        """
        if not payload:
            return ({"elicitation_needed": True,
                     "reason": "get_action_matches: payload is required",
                     "api_error": ["payload: required — provide a dict with at least 'name'"],
                     "message": ("payload is required. Provide a dict with at least 'name', e.g.:\n"
                                 '  {"name": "CPU usage high", "description": "..."}')},)

        if not isinstance(payload, str):
            return payload

        # Try JSON, then quote-fixed JSON, then ast.literal_eval
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(payload.replace("'", '"'))
        except json.JSONDecodeError:
            pass
        try:
            return ast.literal_eval(payload)
        except (SyntaxError, ValueError) as e:
            return ({"elicitation_needed": True,
                     "reason": "get_action_matches: payload is not valid JSON or Python literal",
                     "api_error": [f"payload: could not be parsed — {e}"],
                     "message": f"payload could not be parsed: {e}"},)

    @staticmethod
    def _build_action_search_space(request_body: Dict[str, Any]):
        """
        Import ActionSearchSpace and instantiate it from request_body.

        Returns the object on success or an error dict on failure.
        """
        try:
            from instana_client.models.action_search_space import ActionSearchSpace
            logger.debug("Successfully imported ActionSearchSpace")
        except ImportError as e:
            logger.debug(f"Error importing ActionSearchSpace: {e}")
            return {"error": f"Failed to import ActionSearchSpace: {e!s}"}
        try:
            logger.debug(f"Creating ActionSearchSpace with params: {request_body}")
            obj = ActionSearchSpace(**request_body)
            logger.debug("Successfully created config object")
            return obj
        except Exception as e:
            logger.debug(f"Error creating ActionSearchSpace: {e}")
            return {"error": f"Failed to create config object: {e!s}"}

    def _clean_action_matches_response(self, result_dict: Any) -> Dict[str, Any]:
        """Format and clean a parsed action-matches API response."""
        if not isinstance(result_dict, list):
            logger.debug(f"Result from get_action_matches: {result_dict}")
            return {"success": True, "message": "Action match retrieved successfully", "data": result_dict}

        cleaned_matches = []
        for match in result_dict:
            if isinstance(match, dict) and 'action' in match:
                cleaned_matches.append({
                    "score": match.get("score"),
                    "aiEngine": match.get("aiEngine"),
                    "confidence": match.get("confidence"),
                    "action": self._clean_action_data(match["action"]),
                })
            else:
                cleaned_matches.append(match)

        logger.debug(f"Cleaned {len(cleaned_matches)} action matches (removed ~40-50% of data)")
        return {"success": True, "message": "Action matches retrieved successfully",
                "data": cleaned_matches, "count": len(cleaned_matches)}

    @with_header_auth(ActionCatalogApi)
    async def get_action_matches(self,
                            payload: Union[Dict[str, Any], str],
                            target_snapshot_id: Optional[str] = None,
                            ctx=None,
                            api_client=None,
                            resource_type: Optional[str] = None,
                            tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get action matches for a given action search space and target snapshot ID.
        Args:
            Sample payload:
            {
                "name": "CPU spends significant time waiting for input/output",
                "description": "Checks whether the system spends significant time waiting for input/output."
            }
            target_snapshot_id: Optional[str]: The target snapshot ID to get action matches for.
            ctx: Optional[Dict[str, Any]]: The context to get action matches for.
            api_client: Optional[ActionCatalogApi]: The API client to get action matches for.
        Returns:
            Dict[str, Any]: The action matches for the given payload and target snapshot ID.
        """
        try:
            parsed = self._parse_action_matches_payload(payload)
            if isinstance(parsed, tuple):
                return parsed[0]
            request_body = parsed

            name = request_body.get("name") if isinstance(request_body, dict) else None
            if not name or not str(name).strip():
                return {
                    "elicitation_needed": True,
                    "reason": "get_action_matches has 1 validation problem(s)",
                    "api_error": ["payload.name: required — non-empty string describing the action to search for. "
                                  'Example: "CPU usage high"'],
                    "message": ("The get_action_matches call has 1 problem(s). "
                                "Correct all issues below and retry:\n"
                                '  - payload.name: required — non-empty string describing the action to search for. '
                                'Example: "CPU usage high"'),
                }

            config_object = self._build_action_search_space(request_body)
            if isinstance(config_object, dict):
                return config_object

            logger.debug("Calling get_action_matches_without_preload_content with config object")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_action_matches_without_preload_content,
                    action_search_space=config_object,
                    target_snapshot_id=target_snapshot_id,
                ),
                ctx=ctx, operation_name="get_action_matches",
                resource_type=resource_type, tool_name=tool_name,
            )

            try:
                response_text = result.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug("Successfully retrieved action matches data")
                return self._clean_action_matches_response(result_dict)
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

        except Exception as e:
            logger.error(f"Error in get_action_matches: {e}")
            return {"error": f"Failed to get action matches: {e!s}"}

    def _clean_action_data(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean action data by removing unnecessary fields for LLM consumption.

        Keeps only user-relevant fields:
        - id, name, description, type, tags (core identification)
        - inputParameters (filtered to essential fields)

        Removes internal/technical fields:
        - fields (base64-encoded internal config)
        - metadata (readOnly, builtIn, sensorImported, aiOriginated, ai)
        - createdAt, modifiedAt (epoch timestamps)
        - inputParameter internal flags (hidden, secured, valueType)

        Args:
            action: Raw action dictionary from API

        Returns:
            Cleaned action dictionary optimized for LLM consumption
        """
        cleaned = {
            "id": action.get("id"),
            "name": action.get("name"),
            "description": action.get("description"),
            "type": action.get("type"),
            "tags": action.get("tags", [])
        }

        # Clean input parameters - keep only essential fields
        if action.get("inputParameters"):
            cleaned["inputParameters"] = []
            for param in action["inputParameters"]:
                cleaned_param = {
                    "name": param.get("name"),
                    "label": param.get("label"),
                    "description": param.get("description"),
                    "required": param.get("required", False),
                    "type": param.get("type"),
                    "value": param.get("value")
                }
                cleaned["inputParameters"].append(cleaned_param)

        return cleaned

    @with_header_auth(ActionCatalogApi)
    async def get_actions(self,
                         ctx=None,
                         api_client=None,
                         resource_type: Optional[str] = None,
                         tool_name: Optional[str] = None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get a list of available automation actions from the action catalog.

        Returns cleaned action data optimized for LLM consumption by removing:
        - Internal fields (base64-encoded configs, metadata flags)
        - Timestamps (createdAt, modifiedAt)
        - Technical parameter flags (hidden, secured, valueType)

        Keeps essential fields:
        - id, name, description, type, tags
        - inputParameters (name, label, description, required, type, value)

        Note: The SDK get_actions method does not support pagination or filtering parameters.

        Args:
            ctx: Optional[Dict[str, Any]]: The context for the action retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any]]: The list of cleaned automation actions or error dict
        """
        try:
            logger.debug("get_actions called")

            # Call the get_actions_without_preload_content method from the SDK to avoid Pydantic validation issues
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_actions_without_preload_content),
                ctx=ctx, operation_name="get_actions",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Parse the JSON response manually
            try:
                # The result from get_actions_without_preload_content is a response object
                # We need to read the response data and parse it as JSON
                response_text = result.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug("Successfully retrieved actions data")
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

            # Handle the case where the API returns a list directly
            actions_list = None
            if isinstance(result_dict, list):
                actions_list = result_dict
            elif isinstance(result_dict, dict) and "actions" in result_dict:
                actions_list = result_dict["actions"]
            else:
                # Return as is if format is unexpected
                logger.debug(f"Unexpected format from get_actions: {result_dict}")
                return result_dict

            # Clean the actions data to remove unnecessary fields
            cleaned_actions = [self._clean_action_data(action) for action in actions_list]
            logger.debug(f"Cleaned {len(cleaned_actions)} actions (removed ~40-50% of data)")

            return cleaned_actions

        except Exception as e:
            logger.error(f"Error in get_actions: {e}")
            return {"error": f"Failed to get actions: {e!s}"}

    @with_header_auth(ActionCatalogApi)
    async def get_action_details(self,
                                action_id: str,
                                ctx=None,
                                api_client=None,
                                resource_type: Optional[str] = None,
                                tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific automation action by ID.

        Returns cleaned action data optimized for LLM consumption by removing
        internal fields, timestamps, and technical flags.

        Args:
            action_id: The unique identifier of the action (required)
            ctx: Optional[Dict[str, Any]]: The context for the action details retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Dict[str, Any]: The cleaned detailed information about the automation action
        """
        try:
            # --- Pre-flight ---
            if not action_id or not str(action_id).strip():
                return {
                    "elicitation_needed": True,
                    "reason": "get_action_details: action_id is required",
                    "api_error": ["action_id: required — provide the action UUID (obtain from get_actions)"],
                    "message": (
                        "action_id is required. Obtain it from the get_actions operation first."
                    ),
                }
            # --- End pre-flight ---

            logger.debug(f"get_action_details called with action_id: {action_id}")

            # Call the get_action_by_id_without_preload_content method from the SDK to avoid Pydantic validation issues
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_action_by_id_without_preload_content, id=action_id),
                ctx=ctx, operation_name="get_action_by_id",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Parse the JSON response manually
            try:
                # The result from get_action_by_id_without_preload_content is a response object
                # We need to read the response data and parse it as JSON
                response_text = result.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug("Successfully retrieved action details")
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

            # Clean the action data
            cleaned_action = self._clean_action_data(result_dict)
            logger.debug("Cleaned action details (removed ~40-50% of data)")
            return cleaned_action

        except Exception as e:
            logger.error(f"Error in get_action_details: {e}")
            return {"error": f"Failed to get action details: {e!s}"}

    @with_header_auth(ActionCatalogApi)
    async def get_action_types(self,
                              ctx=None,
                              api_client=None,
                              resource_type: Optional[str] = None,
                              tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a list of available action types in the action catalog.

        Args:
            ctx: Optional[Dict[str, Any]]: The context for the action types retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Dict[str, Any]: The list of available action types
        """
        try:
            logger.debug("get_action_types called")

            # Call the get_actions_without_preload_content method from the SDK to avoid Pydantic validation issues
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_actions_without_preload_content),
                ctx=ctx, operation_name="get_action_types",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Parse the JSON response manually
            try:
                # The result from get_actions_without_preload_content is a response object
                # We need to read the response data and parse it as JSON
                response_text = result.data.decode('utf-8')
                actions_list = json.loads(response_text)
                logger.debug("Successfully retrieved actions data")

                # Extract unique types from actions
                types = set()
                if isinstance(actions_list, list):
                    for action in actions_list:
                        if isinstance(action, dict) and 'type' in action:
                            types.add(action['type'])

                result_dict = {
                    "types": list(types),
                    "total_types": len(types)
                }
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

            logger.debug(f"Result from get_action_types: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_action_types: {e}")
            return {"error": f"Failed to get action types: {e!s}"}

    @with_header_auth(ActionCatalogApi)
    async def get_action_tags(self,
                             ctx=None,
                             api_client=None,
                             resource_type: Optional[str] = None,
                             tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a list of available action tags from the action catalog.

        This method extracts unique 'tags' fields from all actions.

        Args:
            ctx: Optional[Dict[str, Any]]: The context for the action tags retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Dict[str, Any]: The list of available action tags
        """
        try:
            logger.debug("get_action_tags called")

            # Call the get_actions_without_preload_content method from the SDK to avoid Pydantic validation issues
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_actions_without_preload_content),
                ctx=ctx, operation_name="get_action_tags",
                resource_type=resource_type, tool_name=tool_name,
            )

            # Parse the JSON response manually
            try:
                # The result from get_actions_without_preload_content is a response object
                # We need to read the response data and parse it as JSON
                response_text = result.data.decode('utf-8')
                actions_list = json.loads(response_text)
                logger.debug("Successfully retrieved actions data")

                # Extract tags from the actions list
                if isinstance(actions_list, list):
                    # Extract unique tags from actions
                    tags = set()
                    for action in actions_list:
                        if isinstance(action, dict):
                            # Extract tags field
                            if 'tags' in action and isinstance(action['tags'], list):
                                tags.update(action['tags'])

                    result_dict = {
                        "tags": list(tags),
                        "total_tags": len(tags)
                    }
                else:
                    # If it's not a list, return as is
                    result_dict = {
                        "tags": [],
                        "total_tags": 0
                    }

            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}

            logger.debug(f"Result from get_action_tags: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_action_tags: {e}")
            return {"error": f"Failed to get action tags: {e!s}"}

    @staticmethod
    def _preflight_action_matches_by_id(
        application_id: Optional[str],
        snapshot_id: Optional[str],
        to: Optional[int],
        window_size: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        """Validate parameters for get_action_matches_by_id_and_time_window; return elicitation dict or None."""
        errors: list = []

        if not application_id and not snapshot_id:
            errors.append(
                "Either 'application_id' or 'snapshot_id' must be provided. "
                "Example: application_id='app-123'"
            )

        if to is not None:
            if not isinstance(to, int):
                errors.append(
                    f"to: must be an integer Unix timestamp in milliseconds (13 digits), "
                    f"got {type(to).__name__!r}"
                )
            elif to < 1_000_000_000_000 or to > 9_999_999_999_999:
                errors.append(
                    f"to: {to} is not a valid 13-digit millisecond timestamp. "
                    "Example: 1710658800000"
                )

        if window_size is not None:
            if not isinstance(window_size, int):
                errors.append(
                    f"window_size: must be a positive integer (milliseconds), "
                    f"got {type(window_size).__name__!r}"
                )
            elif window_size < 0:
                errors.append(
                    f"window_size: {window_size} must be ≥ 0. "
                    "Example: 3600000 (1 hour)"
                )

        if not errors:
            return None
        return {
            "elicitation_needed": True,
            "reason": f"get_action_matches_by_id_and_time_window has {len(errors)} validation problem(s)",
            "api_error": errors,
            "message": (
                f"The get_action_matches_by_id_and_time_window call has {len(errors)} problem(s). "
                "Correct all issues below and retry:\n"
                + "\n".join(f"  - {e}" for e in errors)
            ),
        }

    def _build_action_matches_by_id_response(
        self,
        result_dict: Any,
        application_id: Optional[str],
        snapshot_id: Optional[str],
        to: Optional[int],
        window_size: Optional[int],
    ) -> Dict[str, Any]:
        """Format and clean a parsed get_action_matches_by_id_and_time_window response."""
        filters = {
            "application_id": application_id,
            "snapshot_id": snapshot_id,
            "to": to,
            "window_size": window_size,
        }

        if isinstance(result_dict, dict) and 'errors' in result_dict:
            error_message = f"API returned error: {result_dict['errors']}"
            logger.error(f"[get_action_matches_by_id_and_time_window] {error_message}")
            return {"error": error_message, "details": result_dict, "filters": filters}

        if not isinstance(result_dict, list):
            logger.debug(f"[get_action_matches_by_id_and_time_window] Result: {result_dict}")
            return {"success": True, "message": "Action matches retrieved successfully", "data": result_dict}

        cleaned_matches = []
        for match in result_dict:
            if isinstance(match, dict) and 'action' in match:
                cleaned_matches.append({
                    "score": match.get("score"),
                    "aiEngine": match.get("aiEngine"),
                    "confidence": match.get("confidence"),
                    "action": self._clean_action_data(match["action"]),
                })
            else:
                cleaned_matches.append(match)

        logger.debug(f"get_action_matches_by_id_and_time_window Cleaned {len(cleaned_matches)} action matches (removed ~40-50% of data)")
        return {
            "success": True,
            "message": "Action matches retrieved successfully",
            "data": cleaned_matches,
            "count": len(cleaned_matches),
            "filters": filters,
        }

    @with_header_auth(ActionCatalogApi)
    async def get_action_matches_by_id_and_time_window(self,
                                                       application_id: Optional[str] = None,
                                                       snapshot_id: Optional[str] = None,
                                                       to: Optional[int] = None,
                                                       window_size: Optional[int] = None,
                                                       ctx=None,
                                                       api_client=None,
                                                       resource_type: Optional[str] = None,
                                                       tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get automation actions that match based on application ID or snapshot ID within a specified time window.

        Args:
            application_id: Optional[str]: Application ID to match actions for
            snapshot_id: Optional[str]: Snapshot ID to match actions for
            to: Optional[int]: End timestamp in milliseconds (13-digit)
            window_size: Optional[int]: Time window size in milliseconds
            ctx: Optional[Dict[str, Any]]: The context for the action matches retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Dict[str, Any]: The list of matching automation actions or error dict

        Example:
            # Get actions matching an application within last hour
            application_id="app-123", window_size=3600000

            # Get actions matching a snapshot at specific time
            snapshot_id="snap-456", to=1234567890000, window_size=600000
        """
        try:
            logger.debug(f"[get_action_matches_by_id_and_time_window] Called with application_id={application_id}, snapshot_id={snapshot_id}, to={to}, window_size={window_size}")

            preflight = self._preflight_action_matches_by_id(application_id, snapshot_id, to, window_size)
            if preflight:
                return preflight

            logger.debug("[get_action_matches_by_id_and_time_window] Calling SDK method")
            result = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_action_matches_by_id_and_time_window_without_preload_content,
                    application_id=application_id,
                    snapshot_id=snapshot_id,
                    to=to,
                    window_size=window_size,
                ),
                ctx=ctx, operation_name="get_action_matches_by_id_and_time_window",
                resource_type=resource_type, tool_name=tool_name,
            )

            try:
                response_text = result.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug("[get_action_matches_by_id_and_time_window] Successfully parsed response")
                return self._build_action_matches_by_id_response(
                    result_dict, application_id, snapshot_id, to, window_size
                )
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(f"[get_action_matches_by_id_and_time_window] {error_message}")
                return {"error": error_message}

        except Exception as e:
            logger.error(f"[get_action_matches_by_id_and_time_window] Error: {e}", exc_info=True)
            return {"error": f"Failed to get action matches by ID and time window: {e!s}"}
