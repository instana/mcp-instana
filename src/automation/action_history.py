"""
Automation Action History MCP Tools Module

This module provides automation action history tools for Instana Automation.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth
from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.action_history_api import (
        ActionHistoryApi,
    )
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import action history API", exc_info=True)
    raise


# Configure logger for this module
logger = logging.getLogger(__name__)

class ActionHistoryMCPTools(BaseInstanaClient):
    """Tools for automation action history in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Action History MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Submit Automation Action",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ActionHistoryApi)
    async def submit_automation_action(self,
                                     payload: Union[Dict[str, Any], str],
                                     ctx=None,
                                     api_client=None) -> Dict[str, Any]:
        """
        Submit an automation action for execution on an agent.
        The automation action to execute and the agent on which to execute the action must be specified as actionId and hostId. For more details on the request payload see the request sample.

        Args:
            Sample payload:
            {
            "hostId": "aHostId",
            "actionId": "d473c1b0-0740-4d08-95fe-31e5d0a9faff",
            "policyId": "2nIOVtEW-iPbsEIi89-yDqJabc",
            "inputParameters": [
                {
                "name": "name",
                "type": "type",
                "value": "value"
                }
            ],
            "eventId": "M3wuBxuaSDyecZJ7ICioiw",
            "async": "true",
            "timeout": "600"
            }

            Required fields:
            - actionId: Action identifier of the action to run
            - hostId: Agent host identifier on which to run the action

            Optional fields:
            - async: "true" if the action should be run in asynchronous mode, "false" otherwise. Default is "true"
            - eventId: Event identifier (incident or issue) associated with the policy
            - policyId: Policy identifier that associates the action trigger to the action to run
            - timeout: Action run time out. Default is 30 seconds
            - inputParameters: Array of action run input parameters

            ctx: Optional[Dict[str, Any]]: The context for the action execution
            api_client: Optional[ActionHistoryApi]: The API client for action execution

        Returns:
            Dict[str, Any]: The result of the automation action submission
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
            required_fields = ["actionId", "hostId"]
            for field in required_fields:
                if field not in request_body:
                    logger.warning(f"Missing required field: {field}")
                    return {"error": f"Missing required field: {field}"}

            # Import the ActionInstanceRequest class
            try:
                from instana_client.models.action_instance_request import (
                    ActionInstanceRequest,
                )
                logger.debug("Successfully imported ActionInstanceRequest")
            except ImportError as e:
                logger.debug(f"Error importing ActionInstanceRequest: {e}")
                return {"error": f"Failed to import ActionInstanceRequest: {e!s}"}

            # Create an ActionInstanceRequest object from the request body
            try:
                logger.debug(f"Creating ActionInstanceRequest with params: {request_body}")
                config_object = ActionInstanceRequest(**request_body)
                logger.debug("Successfully created config object")
            except Exception as e:
                logger.debug(f"Error creating ActionInstanceRequest: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the add_action_instance method from the SDK
            logger.debug("Calling add_action_instance with config object")
            result = api_client.add_action_instance(
                action_instance_request=config_object,
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Automation action submitted successfully"
                }

            logger.debug(f"Result from add_action_instance: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in submit_automation_action: {e}")
            return {"error": f"Failed to submit automation action: {e!s}"}

    @register_as_tool(
        title="Get Action Instance Details",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ActionHistoryApi)
    async def get_action_instance_details(self,
                                        action_instance_id: str,
                                        window_size: Optional[int] = None,
                                        to: Optional[int] = None,
                                        ctx=None,
                                        api_client=None) -> Dict[str, Any]:
        """
        Get the details of an automation action run result by ID from action run history.

        Args:
            action_instance_id: Action run result ID to get action run result details (required)
            window_size: Window size in milliseconds. This value is used to compute the from date (from = to - windowSize) to get the action run result details. The default windowSize is set to 10 minutes if this value is not provided.
            to: To date filter in milliseconds (13-digit) to get the action run result details. The default to date is set to System.currentTimeMillis() if this value is not provided.
            ctx: Optional[Dict[str, Any]]: The context for the action instance retrieval
            api_client: Optional[ActionHistoryApi]: The API client for action history

        Returns:
            Dict[str, Any]: The details of the automation action run result
        """
        try:
            if not action_instance_id:
                return {"error": "action_instance_id is required"}

            logger.debug(f"Getting action instance details for ID: {action_instance_id}")
            result = api_client.get_action_instance(
                action_instance_id=action_instance_id,
                window_size=window_size,
                to=to,
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Action instance details retrieved successfully"
                }

            logger.debug(f"Result from get_action_instance: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_action_instance_details: {e}")
            return {"error": f"Failed to get action instance details: {e!s}"}

    @register_as_tool(
        title="List Action Instances",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ActionHistoryApi)
    async def list_action_instances(self,
                                  window_size: Optional[int] = None,
                                  to: Optional[int] = None,
                                  page: Optional[int] = None,
                                  page_size: Optional[int] = None,
                                  target_snapshot_id: Optional[str] = None,
                                  event_id: Optional[str] = None,
                                  event_specification_id: Optional[str] = None,
                                  search: Optional[str] = None,
                                  types: Optional[List[str]] = None,
                                  action_statuses: Optional[List[str]] = None,
                                  order_by: Optional[str] = None,
                                  order_direction: Optional[str] = None,
                                  ctx=None,
                                  api_client=None) -> Dict[str, Any]:
        """
        Get the details of automation action run results from action run history.

        Args:
            window_size: Window size filter in milliseconds (to compute the from date) to get the action run result details
            to: To date filter in milliseconds (13-digit) to get the action run result details
            page: Page to fetch -- used for paging the action run result records
            page_size: Number of records to return in each page -- used for paging the action run result records
            target_snapshot_id: Target snapshot ID filter to get the action run result details
            event_id: Event ID filter to get the action run result details
            event_specification_id: Event specification ID filter to get the action run result details
            search: Text in action run result name, description and event name filter to get the action run result details
            types: Action type filter to get the action run result details
            action_statuses: Action status filter to get the action run result details
            order_by: Action run result column to order the result set
            order_direction: Sort order direction

            ctx: Optional[Dict[str, Any]]: The context for the action instances retrieval
            api_client: Optional[ActionHistoryApi]: The API client for action history

        Returns:
            Dict[str, Any]: The paginated list of automation action run results
        """
        try:
            logger.debug("Getting action instances with parameters")
            result = api_client.get_action_instances(
                window_size=window_size,
                to=to,
                page=page,
                page_size=page_size,
                target_snapshot_id=target_snapshot_id,
                event_id=event_id,
                event_specification_id=event_specification_id,
                search=search,
                types=types,
                action_statuses=action_statuses,
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
                    "message": "Action instances retrieved successfully"
                }

            logger.debug(f"Result from get_action_instances: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in list_action_instances: {e}")
            return {"error": f"Failed to list action instances: {e!s}"}

    @register_as_tool(
        title="Delete Action Instance",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
    @with_header_auth(ActionHistoryApi)
    async def delete_action_instance(self,
                                   action_instance_id: str,
                                   from_time: int,
                                   to_time: int,
                                   ctx=None,
                                   api_client=None) -> Dict[str, Any]:
        """
        Delete an automation action run result from the action run history by ID.

        Args:
            action_instance_id: Automation action run result ID to delete (required)
            from_time: From date filter in milliseconds (13-digit) to look up the action run result ID (required)
            to_time: To date filter in milliseconds (13-digit) to look up the action run result ID (required)
            ctx: Optional[Dict[str, Any]]: The context for the action instance deletion
            api_client: Optional[ActionHistoryApi]: The API client for action history

        Returns:
            Dict[str, Any]: The result of the action instance deletion
        """
        try:
            if not action_instance_id:
                return {"error": "action_instance_id is required"}
            if not from_time:
                return {"error": "from_time is required"}
            if not to_time:
                return {"error": "to_time is required"}

            logger.debug(f"Deleting action instance with ID: {action_instance_id}")
            result = api_client.delete_action_instance(
                action_instance_id=action_instance_id,
                var_from=from_time,
                to=to_time,
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Action instance deleted successfully"
                }

            logger.debug(f"Result from delete_action_instance: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in delete_action_instance: {e}")
            return {"error": f"Failed to delete action instance: {e!s}"}
