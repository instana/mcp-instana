"""
Log Alert Configuration MCP Tools Module

This module provides log alert configuration-specific MCP tools for Instana monitoring.
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure logger for this module
logger = logging.getLogger(__name__)

# Import the necessary classes from the SDK
try:
    from instana_client.api.log_alert_configuration_api import LogAlertConfigurationApi
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration
    from instana_client.models.log_alert_config import LogAlertConfig
except ImportError:
    logger.error("Failed to import Instana client modules", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth


class LogAlertConfigurationMCPTools(BaseInstanaClient):
    """Tools for log alert configuration in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Log Alert Configuration MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

        try:
            logger.debug(f"Initializing LogAlertConfigurationMCPTools with base_url={base_url}")

            # Configure the API client with the correct base URL and authentication
            configuration = Configuration()
            configuration.host = base_url
            configuration.api_key['ApiKeyAuth'] = read_token
            configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'

            # Create an API client with this configuration
            api_client = ApiClient(configuration=configuration)

            # Initialize the Instana SDK's LogAlertConfigurationApi with our configured client
            self.log_alert_api = LogAlertConfigurationApi(api_client=api_client)
            logger.debug(f"Initialized LogAlertConfigurationApi with host: {configuration.host}")
        except Exception as e:
            logger.error(f"Error initializing LogAlertConfigurationApi: {e}", exc_info=True)
            raise

    @register_as_tool(
        title="Create Log Alert Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def create_log_alert_config(self, config: Dict[str, Any], ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Create a new log alert configuration.

        Args:
            config: Dictionary containing the log alert configuration
                Required fields:
                - name: Name of the alert
                - query: Log query string
                - threshold: Threshold value for the alert
                - timeThreshold: Time threshold in milliseconds
                - rule: Rule configuration
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the created log alert configuration or error information
        """
        try:
            logger.debug(f"create_log_alert_config called with config={config}")

            try:
                # Convert dictionary to LogAlertConfig model
                log_alert_config = LogAlertConfig(**config)
            except Exception as e:
                logger.error(f"Error creating LogAlertConfig: {e}", exc_info=True)
                return {"error": f"Failed to create log alert configuration: {e!s}"}

            try:
                # Call the API
                result = api_client.create_log_alert_config(log_alert_config=log_alert_config)
                logger.debug(f"Result from create_log_alert_config: {result}")

                return self._convert_to_dict(result)
            except Exception as e:
                logger.error(f"Error calling create_log_alert_config API: {e}", exc_info=True)
                return {"error": f"Failed to create log alert configuration: {e!s}"}
        except Exception as e:
            logger.error(f"Error in create_log_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to create log alert configuration: {e!s}"}

    @register_as_tool(
        title="Delete Log Alert Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def delete_log_alert_config(self, id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Delete a log alert configuration.

        Args:
            id: ID of the log alert configuration to delete
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the deletion operation or error information
        """
        try:
            logger.debug(f"delete_log_alert_config called with id={id}")

            try:
                api_client.delete_log_alert_config(id=id)
                logger.debug(f"Successfully deleted log alert configuration with ID {id}")
                return {"success": True, "message": f"Log alert configuration with ID {id} deleted successfully"}
            except Exception as e:
                logger.error(f"Error calling delete_log_alert_config API: {e}", exc_info=True)
                return {"error": f"Failed to delete log alert configuration: {e!s}"}
        except Exception as e:
            logger.error(f"Error in delete_log_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to delete log alert configuration: {e!s}"}

    @register_as_tool(
        title="Disable Log Alert Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def disable_log_alert_config(self, id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Disable a log alert configuration.

        Args:
            id: ID of the log alert configuration to disable
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the disable operation or error information
        """
        try:
            logger.debug(f"disable_log_alert_config called with id={id}")

            try:
                api_client.disable_log_alert_config(id=id)
                logger.debug(f"Successfully disabled log alert configuration with ID {id}")
                return {"success": True, "message": f"Log alert configuration with ID {id} disabled successfully"}
            except Exception as e:
                logger.error(f"Error calling disable_log_alert_config API: {e}", exc_info=True)
                return {"error": f"Failed to disable log alert configuration: {e!s}"}
        except Exception as e:
            logger.error(f"Error in disable_log_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to disable log alert configuration: {e!s}"}

    @register_as_tool(
        title="Enable Log Alert Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def enable_log_alert_config(self, id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Enable a log alert configuration.

        Args:
            id: ID of the log alert configuration to enable
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the enable operation or error information
        """
        try:
            logger.debug(f"enable_log_alert_config called with id={id}")

            try:
                api_client.enable_log_alert_config(id=id)
                logger.debug(f"Successfully enabled log alert configuration with ID {id}")
                return {"success": True, "message": f"Log alert configuration with ID {id} enabled successfully"}
            except Exception as e:
                logger.error(f"Error calling enable_log_alert_config API: {e}", exc_info=True)
                return {"error": f"Failed to enable log alert configuration: {e!s}"}
        except Exception as e:
            logger.error(f"Error in enable_log_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to enable log alert configuration: {e!s}"}

    @register_as_tool(
        title="Find Active Log Alert Configs",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def find_active_log_alert_configs(self, alert_ids: Optional[List[str]] = None, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get all active log alert configurations.

        Args:
            alert_ids: Optional list of alert IDs to filter by
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing active log alert configurations or error information
        """
        try:
            logger.debug(f"find_active_log_alert_configs called with alert_ids={alert_ids}")

            try:
                # Call the API with raw JSON response to avoid Pydantic validation issues
                result = api_client.find_active_log_alert_configs_without_preload_content(alert_ids=alert_ids)
                logger.debug(f"Result from find_active_log_alert_configs: {result}")

                # Parse the JSON response manually
                import json
                try:
                    response_text = result.data.decode('utf-8')
                    result_list = json.loads(response_text)
                    logger.debug("Successfully retrieved active log alert configurations")
                    return {"configs": result_list}
                except (json.JSONDecodeError, AttributeError) as json_err:
                    error_message = f"Failed to parse JSON response: {json_err}"
                    logger.error(error_message)
                    return {"error": error_message}
            except Exception as e:
                logger.error(f"Error calling find_active_log_alert_configs API: {e}", exc_info=True)
                return {"error": f"Failed to find active log alert configurations: {e!s}"}
        except Exception as e:
            logger.error(f"Error in find_active_log_alert_configs: {e}", exc_info=True)
            return {"error": f"Failed to find active log alert configurations: {e!s}"}

    @register_as_tool(
        title="Find Log Alert Config",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def find_log_alert_config(self, id: str, valid_on: Optional[int] = None, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get a specific log alert configuration by ID.

        Args:
            id: ID of the log alert configuration to retrieve
            valid_on: Optional timestamp to get the configuration valid at that time
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the log alert configuration or error information
        """
        try:
            logger.debug(f"find_log_alert_config called with id={id}, valid_on={valid_on}")

            try:
                # Call the API with raw JSON response to avoid Pydantic validation issues
                result = api_client.find_log_alert_config_without_preload_content(id=id, valid_on=valid_on)
                logger.debug(f"Result from find_log_alert_config: {result}")

                # Parse the JSON response manually
                import json
                try:
                    response_text = result.data.decode('utf-8')
                    result_dict = json.loads(response_text)
                    logger.debug("Successfully retrieved log alert configuration")
                    return result_dict
                except (json.JSONDecodeError, AttributeError) as json_err:
                    error_message = f"Failed to parse JSON response: {json_err}"
                    logger.error(error_message)
                    return {"error": error_message}
            except Exception as e:
                logger.error(f"Error calling find_log_alert_config API: {e}", exc_info=True)
                return {"error": f"Failed to find log alert configuration: {e!s}"}
        except Exception as e:
            logger.error(f"Error in find_log_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to find log alert configuration: {e!s}"}

    @register_as_tool(
        title="Find Log Alert Config Versions",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def find_log_alert_config_versions(self, id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get all versions of a log alert configuration.

        Args:
            id: ID of the log alert configuration to get versions for
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing versions of the log alert configuration or error information
        """
        try:
            logger.debug(f"find_log_alert_config_versions called with id={id}")

            try:
                # Call the API with raw JSON response to avoid Pydantic validation issues
                result = api_client.find_log_alert_config_versions_without_preload_content(id=id)
                logger.debug(f"Result from find_log_alert_config_versions: {result}")

                # Parse the JSON response manually
                import json
                try:
                    response_text = result.data.decode('utf-8')
                    result_list = json.loads(response_text)
                    logger.debug("Successfully retrieved log alert configuration versions")
                    return {"versions": result_list}
                except (json.JSONDecodeError, AttributeError) as json_err:
                    error_message = f"Failed to parse JSON response: {json_err}"
                    logger.error(error_message)
                    return {"error": error_message}
            except Exception as e:
                logger.error(f"Error calling find_log_alert_config_versions API: {e}", exc_info=True)
                return {"error": f"Failed to find log alert configuration versions: {e!s}"}
        except Exception as e:
            logger.error(f"Error in find_log_alert_config_versions: {e}", exc_info=True)
            return {"error": f"Failed to find log alert configuration versions: {e!s}"}

    @register_as_tool(
        title="Restore Log Alert Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def restore_log_alert_config(self, id: str, created: int, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Restore a log alert configuration to a previous version.

        Args:
            id: ID of the log alert configuration to restore
            created: Timestamp of the version to restore
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the restore operation or error information
        """
        try:
            logger.debug(f"restore_log_alert_config called with id={id}, created={created}")

            try:
                api_client.restore_log_alert_config(id=id, created=created)
                logger.debug(f"Successfully restored log alert configuration with ID {id}")
                return {
                    "success": True,
                    "message": f"Log alert configuration with ID {id} restored to version from {datetime.fromtimestamp(created/1000).isoformat()}"
                }
            except Exception as e:
                logger.error(f"Error calling restore_log_alert_config API: {e}", exc_info=True)
                return {"error": f"Failed to restore log alert configuration: {e!s}"}
        except Exception as e:
            logger.error(f"Error in restore_log_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to restore log alert configuration: {e!s}"}

    @register_as_tool(
        title="Update Log Alert Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(LogAlertConfigurationApi)
    async def update_log_alert_config(self, id: str, config: Dict[str, Any], ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Update a log alert configuration.

        Args:
            id: ID of the log alert configuration to update
            config: Dictionary containing the updated log alert configuration
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the updated log alert configuration or error information
        """
        try:
            logger.debug(f"update_log_alert_config called with id={id}, config={config}")

            try:
                # Convert dictionary to LogAlertConfig model
                log_alert_config = LogAlertConfig(**config)
            except Exception as e:
                logger.error(f"Error creating LogAlertConfig: {e}", exc_info=True)
                return {"error": f"Failed to update log alert configuration: {e!s}"}

            try:
                # Call the API
                result = api_client.update_log_alert_config(id=id, log_alert_config=log_alert_config)
                logger.debug(f"Result from update_log_alert_config: {result}")
                return self._convert_to_dict(result)
            except Exception as e:
                logger.error(f"Error calling update_log_alert_config API: {e}", exc_info=True)
                return {"error": f"Failed to update log alert configuration: {e!s}"}
        except Exception as e:
            logger.error(f"Error in update_log_alert_config: {e}", exc_info=True)
            return {"error": f"Failed to update log alert configuration: {e!s}"}

    def _convert_to_dict(self, obj: Any) -> Dict[str, Any]:
        """
        Convert an object to a dictionary.

        Args:
            obj: Object to convert

        Returns:
            Dictionary representation of the object
        """
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return obj
