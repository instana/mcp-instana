"""
Mobile App Configuration MCP Tools Module

This module provides mobile app configuration-specific MCP tools for Instana monitoring.
"""

import csv
import io
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

# Import the necessary classes from the SDK
try:
    from instana_client.api.mobile_app_configuration_api import (
        MobileAppConfigurationApi,
    )
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class MobileAppConfigurationMCPTools(BaseInstanaClient):
    """Tools for mobile app configuration in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Mobile App Configuration MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    async def execute_mobile_app_operation(
        self,
        operation: str,
        mobile_app_id: Optional[str] = None,
        mobile_app_name: Optional[str] = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Execute Mobile app CRUD operations. Called by the smart router with appropriate parameters.
        Args:
            operation: The specific operation to perform (get_all, get)
            mobile_app_id: The ID of the mobile app (if applicable)
            mobile_app_name: The name of the mobile app (if applicable)
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the operation or error information
        """
        try:
            if operation == "get_all":
                return await self.get_all_mobile_apps(ctx=ctx)
            elif operation == "get":
                return await self._get_mobile_app(mobile_app_id, mobile_app_name, ctx)
            else:
                return {"error": f"Invalid operation: {operation}"}
        except Exception as e:
            logger.error(f"Error executing mobile app operation '{operation}': {e}", exc_info=True)
            return {"error": f"Failed to execute operation '{operation}': {e!s}"}

    async def execute_mobile_app_advanced_config_operation(
        self,
        operation: str,
        mobile_app_id: Optional[str] = None,
        mobile_app_name: Optional[str] = None,
        config_id: Optional[str] = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Execute advanced configuration retrieval operations (read-only).
        Handles geo-location, IP masking, get_source_map_upload_config, and geo mapping rules.
        Called by the smart router tool.

        Note: Source map operations are available as separate methods but not exposed
        through this executor due to authentication limitations.

        Args:
            operation: Operation to perform (get_geo_config, get_ip_masking, get_geo_rules, get_source_map_upload_config)
            mobile_app_id: Mobile app ID
            mobile_app_name: Mobile app name (for name resolution)
            config_id: Configuration ID (for get_mobile_app_source_map_upload_config_by_id)
            ctx: MCP context

        Returns:
            Operation result dictionary
        """
        try:
            mobile_app_id_or_error = await self._resolve_mobile_app_id(
                mobile_app_id, mobile_app_name, ctx
            )
            if isinstance(mobile_app_id_or_error, dict):
                return mobile_app_id_or_error

            mobile_app_id = mobile_app_id_or_error

            return await self._route_advanced_config_operation(
                operation, mobile_app_id, config_id, ctx
            )

        except Exception as e:
            logger.error(
                f"[execute_mobile_app_advanced_config_operation] Error for operation '{operation}': {e}",
                exc_info=True
            )
            return {"error": f"Failed to execute advanced config operation: {e!s}"}


    async def _resolve_mobile_app_id(
        self,
        mobile_app_id: Optional[str],
        mobile_app_name: Optional[str],
        ctx,
        api_client=None
    ) -> Union[str, Dict[str, Any]]:
        """
        Resolve mobile app ID from either direct ID or name.

        Args:
            mobile_app_id: Direct mobile app ID (if available)
            mobile_app_name: Mobile app name to resolve to ID
            ctx: MCP context
            api_client: API client instance (optional, will use decorator if not provided)

        Returns:
            Mobile app ID string or error dictionary
        """
        # Return ID immediately if provided
        if mobile_app_id:
            return mobile_app_id

        # Validate that at least name is provided
        if not mobile_app_name:
            return {"error": "Either mobile_app_id or mobile_app_name must be provided"}

        logger.debug(f"[_resolve_mobile_app_id] Resolving mobile app name '{mobile_app_name}'")

        # If api_client is provided, use it directly; otherwise fetch via decorator
        if api_client:
            result = await self.get_all_mobile_apps(ctx=ctx, api_client=api_client)
        else:
            # This will trigger the @with_header_auth decorator
            result = await self.get_all_mobile_apps(ctx=ctx)

        logger.debug(f"[_resolve_mobile_app_id] get_all_mobile_apps returned type: {type(result)}, value: {result}")

        # Normalize response to list format
        mobile_apps_list = self._normalize_mobile_apps_response(result)

        if not isinstance(mobile_apps_list, list):
            logger.error(f"[_resolve_mobile_app_id] Unexpected mobile_apps_list type: {type(mobile_apps_list)}, value: {mobile_apps_list}")
            return {"error": "Failed to retrieve mobile apps for name resolution"}

        # Search for matching mobile app by name
        mobile_app_id = self._find_mobile_app_id_by_name(mobile_apps_list, mobile_app_name)

        if mobile_app_id:
            logger.debug(f"[_resolve_mobile_app_id] Resolved '{mobile_app_name}' → '{mobile_app_id}'")
            return mobile_app_id

        # If not found, provide helpful error with available names
        available_names = self._extract_mobile_app_names(mobile_apps_list)
        logger.warning(
            f"[_resolve_mobile_app_id] No mobile app found with name '{mobile_app_name}'. "
            f"Available mobile apps: {available_names}"
        )

        return {"error": f"No mobile app found with name '{mobile_app_name}'"}

    async def _route_advanced_config_operation(
        self,
        operation: str,
        mobile_app_id: str,
        config_id: Optional[str],
        ctx
    ) -> Dict[str, Any]:

        operations_map = {
            "get_geo_config": self.get_mobile_app_geo_location_configuration,
            "get_ip_masking": self.get_mobile_app_ip_masking_configuration,
            "get_geo_rules": self.get_mobile_app_geo_mapping_rules,
            "get_source_map_upload_config": self.get_all_mobile_app_source_map_upload_configurations,
        }

        if operation in operations_map:
            return await operations_map[operation](mobile_app_id, ctx)

        if operation == "get_mobile_app_source_map_upload_config_by_id":
            if not config_id:
                return {"error": "config_id is required for get_mobile_app_source_map_upload_config_by_id operation"}
            return await self.get_mobile_app_source_map_upload_configuration_by_id(
                mobile_app_id, config_id, ctx
            )

        return {
            "error": (
                f"Invalid advanced config operation: {operation}. "
                "Valid operations: get_geo_config, get_ip_masking, "
                "get_geo_rules, get_source_map_upload_config"
            )
        }

    @with_header_auth(MobileAppConfigurationApi)
    async def _get_mobile_app(
        self,
        mobile_app_id: Optional[str],
        mobile_app_name: Optional[str],
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """Get a specific mobile app by ID or name."""

        if not mobile_app_id and mobile_app_name:
            mobile_app_id_or_error = await self._resolve_mobile_app_id(
                mobile_app_id=None,
                mobile_app_name=mobile_app_name,
                ctx=ctx,
                api_client=api_client
            )
            if isinstance(mobile_app_id_or_error, dict):
                return mobile_app_id_or_error

            mobile_app_id = mobile_app_id_or_error

        if not mobile_app_id:
            return {"error": "mobile_app_id or mobile_app_name is required for get operation"}

        return await self.get_mobile_app_by_id(
            mobile_app_id=mobile_app_id,
            ctx=ctx,
            api_client=api_client
        )

    def _normalize_mobile_apps_response(self, response: Any) -> Any:
        if isinstance(response, dict):
            if "results" in response:
                return response["results"]
            return [response]
        return response

    def _find_mobile_app_id_by_name(
        self,
        mobile_apps_list: List[Any],
        mobile_app_name: str
    ) -> Optional[str]:

        for mobile_app in mobile_apps_list:
            name, app_id = self._extract_name_and_id(mobile_app)

            if name and app_id and name.lower() == mobile_app_name.lower():
                logger.debug(f"[_get_mobile_app] Found mobile app '{name}' with ID: {app_id}")
                return app_id

        return None

    def _extract_name_and_id(self, mobile_app: Any) -> Tuple[Optional[str], Optional[str]]:
        if isinstance(mobile_app, dict):
            return mobile_app.get("name"), mobile_app.get("id")

        if hasattr(mobile_app, "name") and hasattr(mobile_app, "id"):
            return mobile_app.name, mobile_app.id

        logger.warning(f"[_get_mobile_app] Unexpected mobile app format: {type(mobile_app)}, {mobile_app}")
        return None, None

    def _extract_mobile_app_names(self, mobile_apps_list: List[Any]) -> List[str]:
        names = []

        for m in mobile_apps_list:
            if isinstance(m, dict):
                names.append(m.get("name", "unknown"))
            elif hasattr(m, "name"):
                names.append(m.name)

        return names

    @with_header_auth(MobileAppConfigurationApi)
    async def get_all_mobile_apps(self, ctx=None, api_client=None) -> List[Dict[str, Any]]:
        """Get all mobile app configurations.

        This API endpoint retrieves all configured mobile apps in your Instana environment.

        Args:
            ctx: Optional context for the API call.

        Returns:
            Dictionary containing mobile app configuration data or error information.
        """
        try:
            logger.debug("[get_all_mobile_apps] Called.")

            result = api_client.get_mobile_app_config()

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            logger.debug(f"[get_all_mobile_apps] Result: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"[get_all_mobile_apps] Error occurred: {e}", exc_info=True)
            return [{"error": f"Failed to get mobile apps: {e!s}"}]

    @with_header_auth(MobileAppConfigurationApi)
    async def get_mobile_app_by_id(self, mobile_app_id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get a specific mobile app by ID.

        This API endpoint retrieves configuration details for a specific mobile app.

        Args:
            mobile_app_id: ID of the mobile app to retrieve
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing mobile app data or error information
        """
        try:
            logger.debug(f"[get_mobile_app_by_id] Called with mobile_app_id: {mobile_app_id}")

            result = api_client.get_single_mobile_app_config(mobile_app_id)

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            logger.debug(f"[get_mobile_app_by_id] Result: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"[get_mobile_app_by_id] Error occurred: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app with ID {mobile_app_id}: {e!s}"}

    @with_header_auth(MobileAppConfigurationApi)
    async def get_mobile_app_geo_location_configuration(self,
                                                        mobile_app_id: str,
                                                        ctx=None,
                                                        api_client=None) -> Dict[str, Any]:
        """
        Get geo location configuration for a specific mobile app.

        This API endpoint retrieves geo location configuration details for a specific mobile app.

        Args:
            mobile_app_id: ID of the mobile app to retrieve geo location configuration for
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing geo location configuration data or error information
        """
        try:
            logger.debug(f"[get_mobile_app_geo_location_configuration] Called with mobile_app_id: {mobile_app_id}")

            result = api_client.get_mobile_app_geo_location_configuration(mobile_app_id)

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            logger.debug(f"[get_mobile_app_geo_location_configuration] Result: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"[get_mobile_app_geo_location_configuration] Error occurred: {e}", exc_info=True)
            return {"error": f"Failed to get geo location configuration for mobile app with ID {mobile_app_id}: {e!s}"}

    @with_header_auth(MobileAppConfigurationApi)
    async def get_mobile_app_geo_mapping_rules(self, mobile_app_id: str, ctx=None, api_client=None) -> List[Dict[str, Any]]:
        """
        Get custom geo mapping rules for mobile app.

        This API endpoint retrieves custom geo mapping rules for a specific mobile app.

        Args:
            mobile_app_id: ID of the mobile app to retrieve geo mapping rules for
            ctx: The MCP context (optional)

        Returns:
            List of dictionaries containing geo mapping rules data or error information
        """
        try:
            logger.debug(f"[get_mobile_app_geo_mapping_rules] Called with mobile_app_id: {mobile_app_id}")

            csv_data = self._fetch_geo_mapping_rules_csv(api_client, mobile_app_id)

            result_list = self._parse_csv_to_dict_list(csv_data)

            logger.debug(f"Result from get_mobile_app_geo_mapping_rules: {result_list}")
            return result_list

        except Exception as e:
            logger.error(f"Error in get_mobile_app_geo_mapping_rules: {e}", exc_info=True)
            return [{"error": f"Failed to get mobile app geo mapping rules: {e!s}"}]

    def _fetch_geo_mapping_rules_csv(self, api_client, mobile_app_id: str) -> str:
        try:
            result = api_client.get_mobile_app_geo_mapping_rules(mobile_app_id)

            if result is not None:
                return str(result)

            return self._fetch_raw_geo_mapping_rules(api_client, mobile_app_id)

        except Exception as api_error:
            logger.warning(f"High-level API call failed: {api_error}, trying raw response")
            return self._fetch_raw_geo_mapping_rules(api_client, mobile_app_id)

    def _fetch_raw_geo_mapping_rules(self, api_client, mobile_app_id: str) -> str:
        response = api_client.get_mobile_app_geo_mapping_rules_without_preload_content(
            mobile_app_id=mobile_app_id
        )

        if hasattr(response, "data"):
            return response.data.decode("utf-8") if isinstance(response.data, bytes) else str(response.data)

        return str(response)

    def _parse_csv_to_dict_list(self, csv_data: str) -> Dict[str, Any]:
        if not csv_data or not csv_data.strip():
            return {
                "status": "empty",
                "data": [],
                "message": "Empty response from API"
            }

        if "," in csv_data:
            csv_reader = csv.DictReader(io.StringIO(csv_data))
            rows = list(csv_reader)

            # Get the field names (headers) from the CSV
            fieldnames = csv_reader.fieldnames if hasattr(csv_reader, 'fieldnames') else []

            if rows:
                return {
                    "status": "success",
                    "data": rows,
                    "schema": fieldnames
                }
            elif fieldnames:
                return {
                    "status": "schema_only",
                    "data": [],
                    "schema": fieldnames,
                    "message": "No geo mapping rules configured, but schema is available"
                }
            else:
                return {
                    "status": "empty",
                    "data": [],
                    "message": "No geo mapping rules configured for this mobile app"
                }

        return {
            "status": "error",
            "data": [],
            "message": f"Unexpected response format: {csv_data}"
        }

    @with_header_auth(MobileAppConfigurationApi)
    async def get_mobile_app_ip_masking_configuration(self, mobile_app_id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get IP masking configuration for a specific mobile app.

        This API endpoint retrieves IP masking configuration details for a specific mobile app.

        Args:
            mobile_app_id: ID of the mobile app to retrieve IP masking configuration for
            ctx: The MCP context (optional)
        Returns:
            Dictionary containing IP masking configuration data or error information
        """
        try:
            logger.debug(f"[get_mobile_app_ip_masking_configuration] Called with mobile_app_id: {mobile_app_id}")

            result = api_client.get_mobile_app_ip_masking_configuration(mobile_app_id=mobile_app_id)

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            logger.debug(f"[get_mobile_app_ip_masking_configuration] Result: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"[get_mobile_app_ip_masking_configuration] Error occurred: {e}", exc_info=True)
            return {"error": f"Failed to get IP masking configuration for mobile app with ID {mobile_app_id}: {e!s}"}

    @with_header_auth(MobileAppConfigurationApi)
    async def get_all_mobile_app_source_map_upload_configurations(
        self,
        mobile_app_id: str,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get all source map upload configurations for a specific mobile app.

        This API endpoint retrieves all source map upload configurations for a specific mobile app.

        Args:
            mobile_app_id: ID of the mobile app to retrieve source map upload configurations for
            ctx: The MCP context (optional)
        Returns:
            Dictionary containing source map upload configuration data or error information
        """
        try:
            logger.debug(f"[get_all_mobile_app_source_map_upload_configurations] Called with mobile_app_id: {mobile_app_id}")

            try:
                response = api_client.get_mobile_app_source_map_files_without_preload_content(mobile_app_id=mobile_app_id)

                if response.status != 200:
                    error_message = f"Failed to get source map configurations: HTTP {response.status}"
                    logger.error(error_message)
                    try:
                        error_body = response.data.decode('utf-8')
                        logger.error(f"Error response body: {error_body}")
                        return {"error": error_message, "details": error_body, "status_code": response.status}
                    except Exception:
                        return {"error": error_message, "status_code": response.status}

                response_text = response.data.decode('utf-8')
                result_dict = json.loads(response_text)
                logger.debug(f"Result from get_all_mobile_app_source_map_upload_configurations: {result_dict}")
                return result_dict

            except Exception as api_error:
                logger.warning(f"without_preload_content failed: {api_error}, trying standard method")
                result = api_client.get_mobile_app_source_map_files(mobile_app_id=mobile_app_id)

                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict()
                else:
                    result_dict = result
                logger.debug(f"Result from get_mobile_app_source_map_files: {result_dict}")
                return result_dict
        except Exception as e:
            logger.error(f"Error in get_all_mobile_app_source_map_upload_configurations: {e}", exc_info=True)
            return {"error": f"Failed to get source map upload configurations for mobile app with ID {mobile_app_id}: {e!s}"}


    @with_header_auth(MobileAppConfigurationApi)
    async def get_mobile_app_source_map_upload_configuration_by_id(
        self,
        mobile_app_id: str,
        source_map_config_id: str,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get a specific source map upload configuration by ID for a mobile app.

        This API endpoint retrieves details for a specific source map upload configuration by its ID for a given mobile app.

        Args:
            mobile_app_id: ID of the mobile app
            source_map_config_id: ID of the source map upload configuration to retrieve
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing source map upload configuration data or error information
        """
        try:
            logger.debug(f"get_mobile_app_source_map_upload_configuration called with mobile_app_id={mobile_app_id}, source_map_config_id={source_map_config_id}")

            try:
                response = api_client.get_mobile_app_source_map_file_without_preload_content(
                    mobile_app_id=mobile_app_id,
                    source_map_config_id=source_map_config_id
                )

                # Check response status
                if response.status != 200:
                    error_message = f"Failed to get source map configuration: HTTP {response.status}"
                    logger.error(error_message)
                    try:
                        error_body = response.data.decode('utf-8')
                        logger.error(f"API Error Response: {error_body}")
                        return {"error": error_message, "details": error_body, "status_code": response.status}
                    except Exception:
                        return {"error": error_message, "status_code": response.status}

                # Parse response
                response_text = response.data.decode('utf-8')
                import json
                result_dict = json.loads(response_text)
                logger.debug(f"Result from get_mobile_app_source_map_file: {result_dict}")
                return result_dict

            except Exception as api_error:
                logger.warning(f"without_preload_content failed: {api_error}, trying standard method")
                # Fallback to standard method
                result = api_client.get_mobile_app_source_map_file(
                    mobile_app_id=mobile_app_id,
                    source_map_config_id=source_map_config_id
                )

                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict()
                else:
                    result_dict = result

                logger.debug(f"Result from get_mobile_app_source_map_file: {result_dict}")
                return result_dict
        except Exception as e:
            logger.error(f"Error in get_mobile_app_source_map_upload_configuration: {e}", exc_info=True)
            return {"error": f"Failed to get mobile app source map upload configuration: {e!s}"}


