"""
Automation Action CAtalog MCP Tools Module

This module provides automation action catalog tools for Instana Automation.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Import the necessary classes from the SDK
try:
    from instana_client.api.action_catalog_api import (
        ActionCatalogApi,
    )
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import application alert configuration API", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class ActionCatalogMCPTools(BaseInstanaClient):
    """Tools for application alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Action Matches",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ActionCatalogApi)
    async def get_action_matches(self,
                            payload: Union[Dict[str, Any], str],
                            target_snapshot_id: Optional[str] = None,
                            ctx=None,
                            api_client=None) -> Dict[str, Any]:
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

            if not payload:
                return {"error": "payload is required"}

            # Parse the payload if it's a string
            if isinstance(payload, str):
                logger.debug("Payload is a string, attempting to parse")
                try:
                    import json
                    try:
                        parsed_payload = json.loads(payload)
                        logger.debug("Successfully parsed payload as JSON")
                        request_body = parsed_payload
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON parsing failed: {e}, trying with quotes replaced")

                        # Try replacing single quotes with double quotes
                        fixed_payload = payload.replace("'", "\"")
                        try:
                            parsed_payload = json.loads(fixed_payload)
                            logger.debug("Successfully parsed fixed JSON")
                            request_body = parsed_payload
                        except json.JSONDecodeError:
                            # Try as Python literal
                            import ast
                            try:
                                parsed_payload = ast.literal_eval(payload)
                                logger.debug("Successfully parsed payload as Python literal")
                                request_body = parsed_payload
                            except (SyntaxError, ValueError) as e2:
                                logger.debug(f"Failed to parse payload string: {e2}")
                                return {"error": f"Invalid payload format: {e2}", "payload": payload}
                except Exception as e:
                    logger.debug(f"Error parsing payload string: {e}")
                    return {"error": f"Failed to parse payload: {e}", "payload": payload}
            else:
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Validate required fields in the payload
            required_fields = ["name"]
            for field in required_fields:
                if field not in request_body:
                    logger.warning(f"Missing required field: {field}")
                    return {"error": f"Missing required field: {field}"}

            # Import the ActionSearchSpace class
            try:
                from instana_client.models.action_search_space import (
                    ActionSearchSpace,
                )
                logger.debug("Successfully imported ActionSearchSpace")
            except ImportError as e:
                logger.debug(f"Error importing ActionSearchSpace: {e}")
                return {"error": f"Failed to import ActionSearchSpace: {e!s}"}

            # Create an ActionSearchSpace object from the request body
            try:
                logger.debug(f"Creating ActionSearchSpace with params: {request_body}")
                config_object = ActionSearchSpace(**request_body)
                logger.debug("Successfully created config object")
            except Exception as e:
                logger.debug(f"Error creating ActionSearchSpace: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the get_action_matches_without_preload_content method from the SDK to avoid Pydantic validation issues
            logger.debug("Calling get_action_matches_without_preload_content with config object")
            result = api_client.get_action_matches_without_preload_content(
                action_search_space=config_object,
                target_snapshot_id=target_snapshot_id,
            )

            # Parse the JSON response manually
            import json
            try:
                # The result from get_action_matches_without_preload_content is a response object
                # We need to read the response data and parse it as JSON
                response_text = result.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug("Successfully retrieved action matches data")

                # Handle the parsed JSON data
                if isinstance(result_dict, list):
                    logger.debug(f"Result from get_action_matches: {result_dict}")
                    return {
                        "success": True,
                        "message": "Action matches retrieved successfully",
                        "data": result_dict,
                        "count": len(result_dict)
                    }
                else:
                    logger.debug(f"Result from get_action_matches: {result_dict}")
                    return {
                        "success": True,
                        "message": "Action match retrieved successfully",
                        "data": result_dict
                    }
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(error_message)
                return {"error": error_message}
        except Exception as e:
            logger.error(f"Error in get_action_matches: {e}")
            return {"error": f"Failed to get action matches: {e!s}"}

    @register_as_tool(
        title="Get Actions",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ActionCatalogApi)
    async def get_actions(self,
                         ctx=None,
                         api_client=None) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Get a list of available automation actions from the action catalog.

        Note: The SDK get_actions method does not support pagination or filtering parameters.

        Args:
            ctx: Optional[Dict[str, Any]]: The context for the action retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any]]: The list of available automation actions or error dict
        """
        try:
            logger.debug("get_actions called")

            # Call the get_actions_without_preload_content method from the SDK to avoid Pydantic validation issues
            result = api_client.get_actions_without_preload_content()

            # Parse the JSON response manually
            import json
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
            if isinstance(result_dict, list):
                # Return the list directly
                logger.debug(f"Result from get_actions: {result_dict}")
                return result_dict
            elif isinstance(result_dict, dict) and "actions" in result_dict:
                logger.debug(f"Result from get_actions: {result_dict['actions']}")
                return result_dict["actions"]
            else:
                # Return as is if it's already a list or other format
                logger.debug(f"Result from get_actions: {result_dict}")
                return result_dict

        except Exception as e:
            logger.error(f"Error in get_actions: {e}")
            return {"error": f"Failed to get actions: {e!s}"}

    @register_as_tool(
        title="Get Action Details",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ActionCatalogApi)
    async def get_action_details(self,
                                action_id: str,
                                ctx=None,
                                api_client=None) -> Dict[str, Any]:
        """
        Get detailed information about a specific automation action by ID.

        Args:
            action_id: The unique identifier of the action (required)
            ctx: Optional[Dict[str, Any]]: The context for the action details retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Dict[str, Any]: The detailed information about the automation action
        """
        try:
            if not action_id:
                return {"error": "action_id is required"}

            logger.debug(f"get_action_details called with action_id: {action_id}")

            # Call the get_action_by_id_without_preload_content method from the SDK to avoid Pydantic validation issues
            result = api_client.get_action_by_id_without_preload_content(id=action_id)

            # Parse the JSON response manually
            import json
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

            logger.debug(f"Result from get_action: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_action_details: {e}")
            return {"error": f"Failed to get action details: {e!s}"}

    @register_as_tool(
        title="Get Action Types",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ActionCatalogApi)
    async def get_action_types(self,
                              ctx=None,
                              api_client=None) -> Dict[str, Any]:
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
            result = api_client.get_actions_without_preload_content()

            # Parse the JSON response manually
            import json
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

    @register_as_tool(
        title="Get Action Tags",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ActionCatalogApi)
    async def get_action_tags(self,
                             ctx=None,
                             api_client=None) -> Dict[str, Any]:
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
            result = api_client.get_actions_without_preload_content()

            # Parse the JSON response manually
            import json
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
