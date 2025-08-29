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

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class ActionCatalogMCPTools(BaseInstanaClient):
    """Tools for application alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool
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

            # Call the get_action_matches method from the SDK
            logger.debug("Calling get_action_matches with config object")
            result = api_client.get_action_matches(
                action_search_space=config_object,
                target_snapshot_id=target_snapshot_id,
            )

            # Convert the result to a dictionary
            if isinstance(result, list):
                # Convert list of ActionMatch objects to list of dictionaries
                result_dict = []
                for action_match in result:
                    try:
                        if hasattr(action_match, 'to_dict'):
                            result_dict.append(action_match.to_dict())
                        else:
                            result_dict.append(action_match)
                    except Exception as e:
                        logger.warning(f"Failed to convert action match to dict: {e}")
                        # Add a fallback representation
                        result_dict.append({
                            "error": f"Failed to serialize action match: {e}",
                            "raw_data": str(action_match)
                        })

                logger.debug(f"Result from get_action_matches: {result_dict}")
                return {
                    "success": True,
                    "message": "Action matches retrieved successfully",
                    "data": result_dict,
                    "count": len(result_dict)
                }
            elif hasattr(result, 'to_dict'):
                try:
                    result_dict = result.to_dict()
                    logger.debug(f"Result from get_action_matches: {result_dict}")
                    return {
                        "success": True,
                        "message": "Action match retrieved successfully",
                        "data": result_dict
                    }
                except Exception as e:
                    logger.warning(f"Failed to convert result to dict: {e}")
                    return {
                        "success": False,
                        "message": "Failed to serialize result",
                        "error": str(e),
                        "raw_data": str(result)
                    }
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Get action matches"
                }
                logger.debug(f"Result from get_action_matches: {result_dict}")
                return result_dict
        except Exception as e:
            logger.error(f"Error in get_action_matches: {e}")
            return {"error": f"Failed to get action matches: {e!s}"}

    @register_as_tool
    @with_header_auth(ActionCatalogApi)
    async def get_actions(self,
                         page: Optional[int] = None,
                         page_size: Optional[int] = None,
                         search: Optional[str] = None,
                         types: Optional[List[str]] = None,
                         order_by: Optional[str] = None,
                         order_direction: Optional[str] = None,
                         ctx=None,
                         api_client=None) -> Dict[str, Any]:
        """
        Get a list of available automation actions from the action catalog.

        Args:
            page: Page number for pagination (optional)
            page_size: Number of actions per page (optional)
            search: Search term to filter actions by name or description (optional)
            types: List of action types to filter by (optional)
            order_by: Field to order results by (optional)
            order_direction: Sort direction ('asc' or 'desc') (optional)
            ctx: Optional[Dict[str, Any]]: The context for the action retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Dict[str, Any]: The list of available automation actions
        """
        try:
            logger.debug("get_actions called")

            # Call the get_actions method from the SDK
            result = api_client.get_actions(
                page=page,
                page_size=page_size,
                search=search,
                types=types,
                order_by=order_by,
                order_direction=order_direction
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Actions retrieved successfully"
                }

            logger.debug(f"Result from get_actions: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_actions: {e}")
            return {"error": f"Failed to get actions: {e!s}"}

    @register_as_tool
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

            # Call the get_action method from the SDK
            result = api_client.get_action(action_id=action_id)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Action details retrieved successfully"
                }

            logger.debug(f"Result from get_action: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_action_details: {e}")
            return {"error": f"Failed to get action details: {e!s}"}

    @register_as_tool
    @with_header_auth(ActionCatalogApi)
    async def search_actions(self,
                            search: str,
                            page: Optional[int] = None,
                            page_size: Optional[int] = None,
                            types: Optional[List[str]] = None,
                            order_by: Optional[str] = None,
                            order_direction: Optional[str] = None,
                            ctx=None,
                            api_client=None) -> Dict[str, Any]:
        """
        Search for automation actions in the action catalog.

        Args:
            search: Search term to find actions by name, description, or other attributes (required)
            page: Page number for pagination (optional)
            page_size: Number of actions per page (optional)
            types: List of action types to filter by (optional)
            order_by: Field to order results by (optional)
            order_direction: Sort direction ('asc' or 'desc') (optional)
            ctx: Optional[Dict[str, Any]]: The context for the action search
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Dict[str, Any]: The search results for automation actions
        """
        try:
            if not search:
                return {"error": "search parameter is required"}

            logger.debug(f"search_actions called with search: {search}")

            # Call the search_actions method from the SDK
            result = api_client.search_actions(
                search=search,
                page=page,
                page_size=page_size,
                types=types,
                order_by=order_by,
                order_direction=order_direction
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Action search completed successfully"
                }

            logger.debug(f"Result from search_actions: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in search_actions: {e}")
            return {"error": f"Failed to search actions: {e!s}"}

    @register_as_tool
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

            # Call the get_action_types method from the SDK
            result = api_client.get_action_types()

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Action types retrieved successfully"
                }

            logger.debug(f"Result from get_action_types: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_action_types: {e}")
            return {"error": f"Failed to get action types: {e!s}"}

    @register_as_tool
    @with_header_auth(ActionCatalogApi)
    async def get_action_categories(self,
                                   ctx=None,
                                   api_client=None) -> Dict[str, Any]:
        """
        Get a list of available action categories in the action catalog.

        Args:
            ctx: Optional[Dict[str, Any]]: The context for the action categories retrieval
            api_client: Optional[ActionCatalogApi]: The API client for action catalog

        Returns:
            Dict[str, Any]: The list of available action categories
        """
        try:
            logger.debug("get_action_categories called")

            # Call the get_action_categories method from the SDK
            result = api_client.get_action_categories()

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Action categories retrieved successfully"
                }

            logger.debug(f"Result from get_action_categories: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_action_categories: {e}")
            return {"error": f"Failed to get action categories: {e!s}"}
