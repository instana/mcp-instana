"""
Application Alert MCP Tools Module

This module provides application alert configuration tools for Instana monitoring.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth
from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.global_application_alert_configuration_api import (
        GlobalApplicationAlertConfigurationApi,
    )
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.error("Failed to import application alert configuration API", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationGlobalAlertMCPTools(BaseInstanaClient):
    """Tools for application alerts in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Alert MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    # CRUD Operations Dispatcher - called by application_smart_router_tool.py
    async def execute_alert_config_operation(
        self,
        operation: str,
        application_id: Optional[str] = None,
        id: Optional[str] = None,
        alert_ids: Optional[List[str]] = None,
        valid_on: Optional[int] = None,
        created: Optional[int] = None,
        payload: Optional[Union[Dict[str, Any], str]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Execute Global Application Alert Config CRUD operations.
        Called by the smart router tool.

        Args:
            operation: Operation to perform (find_active, find_versions, find, create, update, delete, enable, disable, restore)
            application_id: Application ID (for find_active)
            id: Alert config ID
            alert_ids: List of alert IDs to filter
            valid_on: Unix timestamp for specific version
            created: Unix timestamp for restore
            payload: Configuration payload
            ctx: MCP context

        Returns:
            Operation result dictionary
        """
        try:
            if operation == "find_active":
                return await self._find_active_configs(application_id, alert_ids, ctx)
            elif operation == "find_versions":
                return await self._find_config_versions(id, ctx)
            elif operation == "find":
                return await self._find_config(id, valid_on, ctx)
            elif operation == "create":
                return await self._create_config(payload, ctx)
            elif operation == "update":
                return await self._update_config(id, payload, ctx)
            elif operation == "delete":
                return await self._delete_config(id, ctx)
            elif operation == "enable":
                return await self._enable_config(id, ctx)
            elif operation == "disable":
                return await self._disable_config(id, ctx)
            elif operation == "restore":
                return await self._restore_config(id, created, ctx)
            else:
                return {"error": f"Operation '{operation}' not supported"}

        except Exception as e:
            logger.error(f"Error executing {operation}: {e}", exc_info=True)
            return {"error": f"Error executing {operation}: {e!s}"}

    # Individual operation functions

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _find_active_configs(
        self,
        application_id: Optional[str],
        alert_ids: Optional[List[str]],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Find active global application alert configs."""
        if not application_id:
            return {"error": "application_id is required for find_active operation"}

        return await self.find_active_global_application_alert_configs(
            application_id=application_id,
            alert_ids=alert_ids,
            ctx=ctx,
            api_client=api_client
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _find_config_versions(
        self,
        id: Optional[str],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Find all versions of a global application alert config."""
        if not id:
            return {"error": "id is required for find_versions operation"}

        return await self.find_global_application_alert_config_versions(
            id=id,
            ctx=ctx,
            api_client=api_client
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _find_config(
        self,
        id: Optional[str],
        valid_on: Optional[int],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Find a specific global application alert config."""
        return await self.find_global_application_alert_config(
            id=id,
            valid_on=valid_on,
            ctx=ctx,
            api_client=api_client
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _create_config(
        self,
        payload: Optional[Union[Dict[str, Any], str]],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Create a new global application alert config."""
        if not payload:
            return {"error": "payload is required for create operation"}

        return await self.create_global_application_alert_config(
            payload=payload,
            ctx=ctx,
            api_client=api_client
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _update_config(
        self,
        id: Optional[str],
        payload: Optional[Union[Dict[str, Any], str]],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Update an existing global application alert config."""
        if not id:
            return {"error": "id is required for update operation"}
        if not payload:
            return {"error": "payload is required for update operation"}

        return await self.update_global_application_alert_config(
            id=id,
            payload=payload,
            ctx=ctx,
            api_client=api_client
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _delete_config(
        self,
        id: Optional[str],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Delete a global application alert config."""
        if not id:
            return {"error": "id is required for delete operation"}

        return await self.delete_global_application_alert_config(
            id=id,
            ctx=ctx,
            api_client=api_client
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _enable_config(
        self,
        id: Optional[str],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Enable a global application alert config."""
        if not id:
            return {"error": "id is required for enable operation"}

        return await self.enable_global_application_alert_config(
            id=id,
            ctx=ctx,
            api_client=api_client
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _disable_config(
        self,
        id: Optional[str],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Disable a global application alert config."""
        if not id:
            return {"error": "id is required for disable operation"}

        return await self.disable_global_application_alert_config(
            id=id,
            ctx=ctx,
            api_client=api_client
        )

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def _restore_config(
        self,
        id: Optional[str],
        created: Optional[int],
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """Restore a deleted global application alert config."""
        if not id:
            return {"error": "id is required for restore operation"}
        if not created:
            return {"error": "created timestamp is required for restore operation"}

        return await self.restore_global_application_alert_config(
            id=id,
            created=created,
            ctx=ctx,
            api_client=api_client
        )

    # Original individual methods - no @register_as_tool decorator
    # These are called internally by the operation functions above

    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def find_active_global_application_alert_configs(self,
                                            application_id: str,
                                            alert_ids: Optional[List[str]] = None,
                                            ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Get All Global Smart Alert Configuration.

        This tool retrieves all Global Smart Alert Configuration, filtered by application ID and alert IDs.
        This may return a deleted Configuration.

        Configurations are sorted by creation date in descending order.

        Args:
            id: The ID of a specific global application.
            valid_on: A list of Global Smart Alert Configuration IDs. This allows fetching of a specific set of Configurations. This query can be repeated to use multiple IDs.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"find_active_global_application_alert_configs called with application_id={application_id}, alert_ids={alert_ids}")

            # Validate required parameters
            if not application_id:
                return {"error": "application_id is required"}

            # Call the find_active_global_application_alert_configs method from the SDK
            logger.debug(f"Calling find_active_global_application_alert_configs with application_id={application_id}, alert_ids={alert_ids}")
            response = api_client.find_active_global_application_alert_configs_without_preload_content(
                application_id=application_id,
                alert_ids=alert_ids
            )

            import json

            raw_data = response.data.decode('utf-8')
            logger.debug(f"Raw data: {raw_data}")

            try:
                result = json.loads(raw_data)
                logger.debug(f"Parsed JSON result: {result}")

                if isinstance(result, list):
                    configs = result
                else:
                    configs = [result] if result else []

                # Limit to first 10 results
                total_count = len(configs)
                limited_configs = configs[:10]

                # Provide helpful feedback based on the result
                if not configs:
                    return {
                        "configs": [],
                        "count": 0,
                        "total": 0,
                        "showing": 0,
                        "message": f"No active global alert configurations found for application ID: {application_id}",
                        "suggestion": "You can create a new global alert configuration using the 'create' operation."
                    }
                else:
                    return {
                        "configs": limited_configs,
                        "count": len(limited_configs),
                        "total": total_count,
                        "showing": len(limited_configs),
                        "message": f"Found {total_count} active global alert configuration(s) for application ID: {application_id}. Showing first {len(limited_configs)}."
                    }

            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse response JSON: {e}"
                logger.error(error_msg)
                return {"error": error_msg}

        except Exception as e:
            logger.error(f"Error in find_active_global_application_alert_configs: {e}", exc_info=True)
            return {"error": f"Failed to get active global application alert config: {e!s}"}


    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def find_global_application_alert_config_versions(self,
                                                     id: str,
                                                     ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Get Global Smart Alert Config Versions . Get all versions of Global Smart Alert Configuration.

        This tool retrievesGets all versions of a Global Smart Alert Configuration.
        This may return deleted Configurations. Configurations are sorted by creation date in descending order.

        Args:
            id: ID of a specific Global Smart Alert Configuration to retrieve.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the Smart Alert Configuration versions or error information
        """
        try:
            logger.debug(f"find_global_application_alert_config_versions called with id={id}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the find_global_application_alert_config_versions method from the SDK
            logger.debug(f"Calling find_global_application_alert_config_versions with id={id}")
            result = api_client.find_global_application_alert_config_versions(
                id=id
            )

            # Convert the result to a dictionary
            if isinstance(result, list):
                # If result is a list, convert each item to a dictionary and wrap in a dict
                items = [item.to_dict() if hasattr(item, 'to_dict') else item for item in result]
                result_dict = {"versions": items}
            elif hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result if isinstance(result, dict) else {"data": result}

            logger.debug(f"Result from find_global_application_alert_config_versions: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in find_global_application_alert_config_versions: {e}", exc_info=True)
            return {"error": f"Failed to get global application alert config versions: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def find_global_application_alert_config(self,
                                            id: Optional[str] = None,
                                            valid_on: Optional[int] = None,
                                            ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Gets a specific Global Smart Alert Configuration. This may return a deleted Configuration.

        This tool retrieves Global Smart Alert Configurations, filtered by id and valid on.

        Args:
            id: ID of a specific Global Smart Alert Configuration to retrieve
            valid_on: A Unix timestamp representing a specific time the Configuration was active. If no timestamp is provided, the latest active version will be retrieved.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing Smart Alert Configurations or error information
        """
        try:
            logger.debug(f"get_application_alert_configs called with id={id}, valid_on={valid_on}")

            # Call the find_global_application_alert_config method from the SDK
            logger.debug(f"Calling find_global_application_alert_config with id={id}, valid_on={valid_on}")
            result = api_client.find_global_application_alert_config(
                id=id,
                valid_on=valid_on
            )

            # Convert the result to a dictionary
            if isinstance(result, list):
                # If result is a list, convert each item to a dictionary and wrap in a dict
                items = [item.to_dict() if hasattr(item, 'to_dict') else item for item in result]
                result_dict = {"configs": items}
            elif hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result if isinstance(result, dict) else {"data": result}

            logger.debug(f"Result from find_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in find_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to get global application alert configs: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def delete_global_application_alert_config(self,
                                              id: str,
                                              ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Deletes a Global Smart Alert Configuration.

        This tool deletes a specific Global Smart Alert Configuration by its ID.
        Once deleted, the configuration will no longer trigger alerts.

        Args:
            id: ID of a specific Global Smart Alert Configuration to delete.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the deletion operation or error information
        """
        try:
            logger.debug(f"delete_global_application_alert_config called with id={id}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the delete_global_application_alert_config method from the SDK
            logger.debug(f"Calling delete_global_application_alert_config with id={id}")
            api_client.delete_global_application_alert_config(id=id)

            # The delete operation doesn't return a result, so we'll create a success message
            result_dict = {
                "success": True,
                "message": f"Global Smart Alert Configuration with ID '{id}' has been successfully deleted"
            }

            logger.debug(f"Result from delete_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in delete_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to delete global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def enable_global_application_alert_config(self,
                                              id: str,
                                              ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Enable a Global Smart Alert Configuration.

        This tool enables a specific Global Smart Alert Configuration by its ID.
        Once enabled, the configuration will start triggering alerts when conditions are met.

        Args:
            id: ID of a specific Global Smart Alert Configuration to enable.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the enable operation or error information
        """
        try:
            logger.debug(f"enable_global_application_alert_config called with id={id}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the enable_global_application_alert_config method from the SDK
            logger.debug(f"Calling enable_global_application_alert_config with id={id}")
            result = api_client.enable_global_application_alert_config(id=id)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": f"Global Smart Alert Configuration with ID '{id}' has been successfully enabled"
                }

            logger.debug(f"Result from enable_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in enable_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to enable global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def disable_global_application_alert_config(self,
                                               id: str,
                                               ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Disable a Global Smart Alert Configuration.

        This tool disables a specific Smart Alert Configuration by its ID.
        Once disabled, the configuration will stop triggering alerts even when conditions are met.

        Args:
            id: ID of a specific Global Smart Alert Configuration to disable.
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the disable operation or error information
        """
        try:
            logger.debug(f"disable_global_application_alert_config called with id={id}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            # Call the disable_global_application_alert_config method from the SDK
            logger.debug(f"Calling disable_global_application_alert_config with id={id}")
            result = api_client.disable_global_application_alert_config(id=id)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": f"Smart Alert Configuration with ID '{id}' has been successfully disabled"
                }

            logger.debug(f"Result from disable_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in disable_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to disable global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def restore_global_application_alert_config(self,
                                               id: str,
                                               created: int,
                                               ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Restore a deleted Global Smart Alert Configuration.

        This tool restores a previously deleted Global Smart Alert Configuration by its ID and creation timestamp.
        Once restored, the configuration will be active again and can trigger alerts when conditions are met.

        Args:
            id: ID of a specific Global Smart Alert Configuration to restore.
            created: Unix timestamp representing the creation time of the specific Global Smart Alert Configuration version
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the restore operation or error information
        """
        try:
            logger.debug(f"restore_global_application_alert_config called with id={id}, created={created}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

            if not created:
                return {"error": "created timestamp is required"}

            # Call the restore_global_application_alert_config method from the SDK
            logger.debug(f"Calling restore_global_application_alert_config with id={id}, created={created}")
            result = api_client.restore_global_application_alert_config(id=id, created=created)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": f"Global Smart Alert Configuration with ID '{id}' and creation timestamp '{created}' has been successfully restored"
                }

            logger.debug(f"Result from restore_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in restore_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to restore global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def create_global_application_alert_config(self,
                                              payload: Union[Dict[str, Any], str],
                                              ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Creates a new Global Smart Alert Configuration.

        This tool creates a new Global Smart Alert Configuration with the provided configuration details.
        Once created, the configuration will be active and can trigger alerts when conditions are met.

        Sample payload:
        {
        "name": "Slow calls than usual",
        "description": "Calls are slower or equal to 2 ms based on latency (90th).",
        "boundaryScope": "INBOUND",
        "applications": {
            "j02SxMRTSf-NCBXf5IdsjQ": {
            "applicationId": "j02SxMRTSf-NCBXf5IdsjQ",
            "inclusive": true,
            "services": {}
            }
        },
        "applicationIds": [
            "j02SxMRTSf-NCBXf5IdsjQ"
        ],
        "severity": 5,
        "triggering": false,
        "tagFilterExpression": {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": []
        },
        "includeInternal": false,
        "includeSynthetic": false,
        "rule": {
            "alertType": "slowness",
            "aggregation": "P90",
            "metricName": "latency"
        },
        "threshold": {
            "type": "staticThreshold",
            "operator": ">=",
            "value": 2,
            "lastUpdated": 0
        },
        "alertChannelIds": [],
        "granularity": 600000,
        "timeThreshold": {
            "type": "violationsInSequence",
            "timeWindow": 600000
        },
        "evaluationType": "PER_AP",
        "customPayloadFields": []
        }

        Args:
            payload: The Global Smart Alert Configuration details as a dictionary or JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the created new Global Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"create_global_application_alert_config called with payload={payload}")

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

            # Validate the payload
            if not request_body:
                return {"error": "Payload is required"}

            # Import the GlobalApplicationsAlertConfig class
            try:
                from instana_client.models.global_applications_alert_config import (
                    GlobalApplicationsAlertConfig,
                )
                logger.debug("Successfully imported GlobalApplicationsAlertConfig")
            except ImportError as e:
                logger.debug(f"Error importing GlobalApplicationsAlertConfig: {e}")
                return {"error": f"Failed to import GlobalApplicationsAlertConfig: {e!s}"}

            # Create an GlobalApplicationsAlertConfig object from the request body
            try:
                logger.debug(f"Creating GlobalApplicationsAlertConfig with params: {request_body}")
                config_object = GlobalApplicationsAlertConfig(**request_body)
                logger.debug("Successfully created config object")
            except Exception as e:
                logger.debug(f"Error creating GlobalApplicationsAlertConfig: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the create_global_application_alert_config method from the SDK
            logger.debug("Calling create_global_application_alert_config with config object")
            result = api_client.create_global_application_alert_config(global_applications_alert_config=config_object)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from create_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in create_global_application_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to create global application alert config: {e!s}"}

    # @register_as_tool decorator removed - now called via router
    @with_header_auth(GlobalApplicationAlertConfigurationApi)
    async def update_global_application_alert_config(self,
                                              id: str,
                                              payload: Union[Dict[str, Any], str],
                                              ctx: Optional[Context] = None, api_client: Any = None) -> Dict[str, Any]:
        """
        Update an existing Global Smart Alert Configuration.

        This tool updates an existing Global Smart Alert Configuration with the provided configuration details.
        The configuration is identified by its ID, and the payload contains the updated configuration.

        Sample payload:
        {
        "name": "Slow calls than usual",
        "description": "Calls are slower or equal to 2 ms based on latency (90th).",
        "boundaryScope": "INBOUND",
        "applications": {
            "j02SxMRTSf-NCBXf5IdsjQ": {
            "applicationId": "j02SxMRTSf-NCBXf5IdsjQ",
            "inclusive": true,
            "services": {}
            }
        },
        "applicationIds": [
            "j02SxMRTSf-NCBXf5IdsjQ"
        ],
        "severity": 5,
        "triggering": false,
        "tagFilterExpression": {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": []
        },
        "includeInternal": false,
        "includeSynthetic": false,
        "rule": {
            "alertType": "slowness",
            "aggregation": "P90",
            "metricName": "latency"
        },
        "threshold": {
            "type": "staticThreshold",
            "operator": ">=",
            "value": 2,
            "lastUpdated": 0
        },
        "alertChannelIds": [],
        "granularity": 600000,
        "timeThreshold": {
            "type": "violationsInSequence",
            "timeWindow": 600000
        },
        "evaluationType": "PER_AP",
        "customPayloadFields": []
        }

        Args:
            id: The ID of the Global Smart Alert Configuration to update
            payload: The updated Global Smart Alert Configuration details as a dictionary or JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the updated Global Smart Alert Configuration or error information
        """
        try:
            logger.debug(f"update_global_application_alert_config called with id={id}, payload={payload}")

            # Validate required parameters
            if not id:
                return {"error": "id is required"}

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

            # Import the GlobalApplicationsAlertConfig class
            try:
                from instana_client.models.global_applications_alert_config import (
                    GlobalApplicationsAlertConfig,
                )
                logger.debug("Successfully imported GlobalApplicationsAlertConfig")
            except ImportError as e:
                logger.debug(f"Error importing GlobalApplicationsAlertConfig: {e}")
                return {"error": f"Failed to import GlobalApplicationsAlertConfig: {e!s}"}

            # Create an GlobalApplicationsAlertConfig object from the request body
            try:
                logger.debug(f"Creating GlobalApplicationsAlertConfig with params: {request_body}")
                config_object = GlobalApplicationsAlertConfig(**request_body)
                logger.debug("Successfully created config object")
            except Exception as e:
                logger.debug(f"Error creating ApplicationAlertConfig: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the update_global_application_alert_config method from the SDK
            logger.debug(f"Calling update_global_application_alert_config with id={id} and config object")
            result = api_client.update_global_application_alert_config(
                id=id,
                global_applications_alert_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": f"Smart Global Alert Configuration with ID '{id}' has been successfully updated"
                }

            logger.debug(f"Result from update_global_application_alert_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in update_global_application_alert_config: {e}")
            return {"error": f"Failed to update global application alert config: {e!s}"}


