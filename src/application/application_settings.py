"""
Application Settings MCP Tools Module

This module provides application settings-specific MCP tools for Instana monitoring.

The API endpoints of this group provides a way to create, read, update, delete (CRUD) for various configuration settings.
"""

import re
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Import the necessary classes from the SDK
try:
    from instana_client.api.application_settings_api import ApplicationSettingsApi
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration
    from instana_client.models.application_config import ApplicationConfig
    from instana_client.models.endpoint_config import EndpointConfig
    from instana_client.models.manual_service_config import ManualServiceConfig
    from instana_client.models.new_application_config import NewApplicationConfig
    from instana_client.models.new_manual_service_config import NewManualServiceConfig
    from instana_client.models.service_config import ServiceConfig
except ImportError as e:
    print(f"Error importing Instana SDK: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    raise


# Helper function for debug printing
def debug_print(*args, **kwargs):
    """Print debug information to stderr instead of stdout"""
    print(*args, file=sys.stderr, **kwargs)

class ApplicationSettingsMCPTools(BaseInstanaClient):
    """Tools for application settings in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Settings MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

        try:

            # Configure the API client with the correct base URL and authentication
            configuration = Configuration()
            configuration.host = base_url
            configuration.api_key['ApiKeyAuth'] = read_token
            configuration.api_key_prefix['ApiKeyAuth'] = 'apiToken'

            # Create an API client with this configuration
            api_client = ApiClient(configuration=configuration)

            # Initialize the Instana SDK's ApplicationSettingsApi with our configured client
            self.settings_api = ApplicationSettingsApi(api_client=api_client)
        except Exception as e:
            debug_print(f"Error initializing ApplicationSettingsApi: {e}")
            traceback.print_exc(file=sys.stderr)
            raise

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def get_all_applications_configs(self,
                             ctx=None,
                             api_client=None) -> List[Dict[str, Any]]:
        """
        All Application Perspectives Configuration
        Get a list of all Application Perspectives with their configuration settings.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            debug_print("Fetching all applications and their settings")
            result = api_client.get_application_configs()
            # Convert the result to a list of dictionaries
            if isinstance(result, list):
                result_dict = [item.to_dict() if hasattr(item, 'to_dict') else item for item in result]
            elif hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            debug_print(f"Result from get_application_configs: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in get_application_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return [{"error": f"Failed to get all applications: {e!s}"}]

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def add_application_config(self,
                               access_rules: List[Dict[str, str]],
                               boundary_scope: str,
                               label: str,
                               scope: str,
                               tag_filter_expression: Optional[List[Dict[str, str]]] = None,
                               ctx=None,
                               api_client=None) -> Dict[str, Any]:
        """
        Add a new Application Perspective configuration.
        This tool allows you to create a new Application Perspective with specified settings.
        Args:
            accessRules: List of access rules for the application perspective
            boundaryScope: Boundary scope for the application perspective
            label: Label for the application perspective
            scope: Scope of the application perspective
            tagFilterExpression: Tag filter expression for the application perspective (Optional)
            ctx: The MCP context (optional)
        Returns:
            Dictionary containing the created application perspective configuration or error information
        """
        try:
            debug_print("Adding new application perspective configuration")
            if not (access_rules or boundary_scope or label or scope):
                return {"error": "Required enitities are missing or invalid"}

            # Create a NewApplicationConfig instance with the provided parameters
            request_body = {
                "access_rules": access_rules,
                "boundary_scope": boundary_scope,
                "label": label,
                "scope": scope,
                "tag_filter_expression": tag_filter_expression
            }
            new_application_config = NewApplicationConfig(**request_body)
            debug_print(f"New Application Config: {new_application_config.to_dict()}")

            # Call the add_application_config method from the SDK
            result = api_client.add_application_config(
                new_application_config=new_application_config
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            debug_print(f"Result from add_application_config: {result_dict}")
            return result_dict
        except Exception as e:
            debug_print(f"Error in add_application_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to add application configuration: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def delete_application_config(self,
                                  id: str,
                                  ctx=None,
                                  api_client=None) -> Dict[str, Any]:
        """
        Delete an Application Perspective configuration.
        This tool allows you to delete an existing Application Perspective by its ID.

        Args:
            application_id: The ID of the application perspective to delete
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the deletion or error information
        """
        try:
            if not id:
                return {"error": "Application perspective ID is required for deletion"}


            debug_print(f"Deleting application perspective with ID: {id}")
            # Call the delete_application_config method from the SDK
            self.settings_api.delete_application_config(id=id)

            result_dict = {
                "success": True,
                "message": f"Application Confiuguration '{id}' has been successfully deleted"
            }

            debug_print(f"Successfully deleted application perspective with ID: {id}")
            return result_dict
        except Exception as e:
            debug_print(f"Error in delete_application_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to delete application configuration: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def get_application_config(self,
                                  id: str,
                                  ctx=None,
                                  api_client=None) -> Dict[str, Any]:
        """
        Get an Application Perspective configuration by ID.
        This tool retrieves the configuration settings for a specific Application Perspective.

        Args:
            id: The ID of the application perspective to retrieve
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the application perspective configuration or error information
        """
        try:
            debug_print(f"Fetching application perspective with ID: {id}")
            # Call the get_application_config method from the SDK
            result = api_client.get_application_config(id=id)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            debug_print(f"Result from get_application_config: {result_dict}")
            return result_dict
        except Exception as e:
            debug_print(f"Error in get_application_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to get application configuration: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def update_application_config(
        self,
        id: str,
        access_rules: List[Dict[str, str]],
        boundary_scope: str,
        label: str,
        scope: str,
        tag_filter_expression: Optional[List[Dict[str, str]]] = None,
        match_specification: Optional[List[Dict[str, Any]]] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Update an existing Application Perspective configuration.
        This tool allows you to update an existing Application Perspective with specified application Id.

        Args:
            id: The ID of the application perspective to retrieve
            access_rules: List of access rules for the application perspective
            boundary_scope: Boundary scope for the application perspective
            label: Label for the application perspective
            scope: Scope of the application perspective
            tag_filter_expression: Tag filter expression for the application perspective (Optional)
            ctx: The MCP context (optional)
        Returns:
            Dictionary containing the created application perspective configuration or error information
        """

        try:
            debug_print("Update existing application perspective configuration")
            if not (access_rules or boundary_scope or label or scope or id):
                return {"error": "Required enitities are missing or invalid"}

            request_body = {
                "access_rules": access_rules,
                "boundary_scope": boundary_scope,
                "id": id,
                "label": label,
                "match_specification": match_specification,
                "scope": scope,
                "tag_filter_expression": tag_filter_expression
            }
            # Create a ApplicationConfig instance with the provided parameters
            application_config = ApplicationConfig(**request_body)
            debug_print(f"Application Config: {application_config.to_dict()}")

            # Call the put_application_config method from the SDK
            result = api_client.put_application_config(
                id=id,
                application_config=application_config
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            debug_print(f"Result from put_application_config: {result_dict}")
            return result_dict
        except Exception as e:
            debug_print(f"Error in put_application_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to update application configuration: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def get_all_endpoint_configs(self,
                             ctx=None,
                             api_client=None) -> List[Dict[str, Any]]:
        """
        All Endpoint Perspectives Configuration
        Get a list of all Endpoint Perspectives with their configuration settings.
        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            debug_print("Fetching all endpoint configs")
            result = api_client.get_endpoint_configs()
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from get_endpoint_configs: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in get_endpoint_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return [{"error": f"Failed to get endpoint configs: {e!s}"}]

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def create_endpoint_config(
        self,
        endpoint_case: str,
        service_id: str,
        endpoint_name_by_collected_path_template_rule_enabled: Optional[bool]= None,
        endpoint_name_by_first_path_segment_rule_enabled: Optional[bool] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Create or update endpoint configuration for a service.

        Args:
            serviceId (str): Instana Service ID to configure.
            endpointCase (str): Case format for endpoints. One of: 'ORIGINAL', 'LOWER', 'UPPER'.
            endpointNameByCollectedPathTemplateRuleEnabled (Optional[bool]): Enable path template rule. (Optional)
            endpointNameByFirstPathSegmentRuleEnabled (Optional[bool]): Enable first path segment rule. (Optional)
            rules (Optional[List[Dict[str, Any]]]): Optional list of custom HTTP endpoint rules. (Optional)
            ctx: The MCP context (optional)

        Returns:
            Dict[str, Any]: Response from the create/update endpoint configuration API.
        """
        try:
            debug_print("Creating endpoint configs")
            if not endpoint_case or not service_id:
                return {"error": "Required enitities are missing or invalid"}

            request_body = {
                "endpoint_case": endpoint_case,
                "endpoint_name_by_collected_path_template_rule_enabled": endpoint_name_by_collected_path_template_rule_enabled,
                "endpoint_name_by_first_path_segment_rule_enabled": endpoint_name_by_first_path_segment_rule_enabled,
                "rules": rules,
                "serviceId": service_id
            }
            endpoint_config = EndpointConfig(**request_body)

            result = api_client.create_endpoint_config(
                endpoint_config=endpoint_config
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from get_endpoint_configs: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in get_endpoint_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to get endpoint configs: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def delete_endpoint_config(
        self,
        id: str,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Delete an endpoint configuration of a service.

        Args:
            id: An Instana generated unique identifier for a Service.
            ctx: The MCP context (optional)

        Returns:
            Dict[str, Any]: Response from the delete endpoint configuration API.
        """
        try:
            debug_print("Delete endpoint configs")
            if not id:
                return {"error": "Required enitities are missing or invalid"}

            api_client.delete_endpoint_config(id=id)

            result_dict = {
                "success": True,
                "message": f"Endpoint Confiuguration '{id}' has been successfully deleted"
            }

            debug_print(f"Successfully deleted endpoint perspective with ID: {id}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in delete_endpoint_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to delete endpoint configs: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def get_endpoint_config(
        self,
        id: str,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        This MCP tool is used for endpoint if one wants to retrieve the endpoint configuration of a service.
        Args:
            id: An Instana generated unique identifier for a Service.
            ctx: The MCP context (optional)

        Returns:
            Dict[str, Any]: Response from the create/update endpoint configuration API.

        """
        try:
            debug_print("get endpoint config")
            if not id:
                return {"error": "Required enitities are missing or invalid"}

            result = api_client.get_endpoint_config(
                id=id
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from get_endpoint_configs: {result_dict}")
            return result_dict
        except Exception as e:
            debug_print(f"Error in get_endpoint_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to get endpoint configs: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def update_endpoint_config(
        self,
        id: str,
        endpoint_case: str,
        service_id: str,
        endpoint_name_by_collected_path_template_rule_enabled: Optional[bool]= None,
        endpoint_name_by_first_path_segment_rule_enabled: Optional[bool] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        update endpoint configuration for a service.

        Args:
            id: An Instana generated unique identifier for a Service.
            serviceId: Instana Service ID to configure.
            endpointCase: Case format for endpoints. One of: 'ORIGINAL', 'LOWER', 'UPPER'.
            endpointNameByCollectedPathTemplateRuleEnabled: Enable path template rule. (Optional)
            endpointNameByFirstPathSegmentRuleEnabled: Enable first path segment rule. (Optional)
            rules: Optional list of custom HTTP endpoint rules. (Optional)
            ctx: The MCP context (optional)

        Returns:
            Dict[str, Any]: Response from the create/update endpoint configuration API.
        """
        try:
            debug_print("Updating endpoint configs")
            if not endpoint_case or not service_id:
                return {"error": "Required enitities are missing or invalid"}

            request_body = {
                "endpoint_case": endpoint_case,
                "endpoint_name_by_collected_path_template_rule_enabled": endpoint_name_by_collected_path_template_rule_enabled,
                "endpoint_name_by_first_path_segment_rule_enabled": endpoint_name_by_first_path_segment_rule_enabled,
                "rules": rules,
                "serviceId": service_id
            }
            endpoint_config = EndpointConfig(**request_body)

            result = api_client.update_endpoint_config(
                id=id,
                endpoint_config=endpoint_config
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from get_endpoint_configs: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in get_endpoint_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to get endpoint configs: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def get_all_manual_service_configs(self,
                             ctx=None,
                             api_client=None) -> List[Dict[str, Any]]:
        """
        All Manual Service Perspectives Configuration
        Get a list of all Manual Service Perspectives with their configuration settings.
        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            debug_print("Fetching all manual configs")
            result = api_client.get_all_manual_service_configs()
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from get_all_manual_service_configs: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in get_all_manual_service_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return [{"error": f"Failed to get manual service configs: {e!s}"}]

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def add_manual_service_config(
        self,
        tagFilterExpression: Dict[str, Any],
        unmonitoredServiceName: Optional[str] = None,
        existingServiceId: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = True,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Create a manual service mapping configuration.

        Requires `CanConfigureServiceMapping` permission on the API token.

        Args:
            tagFilterExpression : Boolean expression of tag filters to match relevant calls.
            unmonitoredServiceName : Custom name for an unmonitored service to map. (Optional)
            existingServiceId : Service ID to link the matched calls to. (Optional)
            description : Description of the mapping configuration. (Optional)
            enabled : Enable or disable the configuration. Defaults to True. (Optional)
            ctx: Optional execution context.

        Returns:
            Dict[str, Any]: API response indicating success or failure.
        """
        try:
            debug_print("Creating manual service configuration")

            if not (unmonitoredServiceName and existingServiceId):
                return {
                    "error": "You must provide either 'unmonitoredServiceName' or 'existingServiceId'."
                }

            if not tagFilterExpression:
                return {"error": "Required enitities are missing or invalid"}


            body = {
                "tagFilterExpression": tagFilterExpression,
                "enabled": enabled
            }

            if unmonitoredServiceName:
                body["unmonitoredServiceName"] = unmonitoredServiceName
            if existingServiceId:
                body["existingServiceId"] = existingServiceId
            if description:
                body["description"] = description

            new_manual_service_config = NewManualServiceConfig(**body)

            result = api_client.add_manual_service_config(
                new_manual_service_config=new_manual_service_config
            )

            if hasattr(result, "to_dict"):
                result_dict = result.to_dict()
            else:
                result_dict = result

            debug_print(f"Manual service configuration result: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error creating manual service configuration: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to create manual service configuration: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def delete_manual_service_config(
        self,
        id: str,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Delete a manual service configuration.

        Args:
            id: A unique id of the manual service configuration.
            ctx: The MCP context (optional)

        Returns:
            Dict[str, Any]: Response from the delete manual service configuration API.
        """
        try:
            debug_print("Delete manual service configs")
            if not id:
                return {"error": "Required enitities are missing or invalid"}

            api_client.delete_manual_service_config(id=id)

            result_dict = {
                "success": True,
                "message": f"Manual Service Confiuguration '{id}' has been successfully deleted"
            }

            debug_print(f"Successfully deleted manual service config perspective with ID: {id}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in delete_manual_service_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to delete manual service configs: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def update_manual_service_config(
        self,
        id: str,
        tagFilterExpression: Dict[str, Any],
        unmonitoredServiceName: Optional[str] = None,
        existingServiceId: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = True,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        The manual service configuration APIs enables mapping calls to services using tag filter expressions based on call tags.

        There are two use cases on the usage of these APIs:

        Map to an Unmonitored Service with a Custom Name. For example, Map HTTP calls to different Google domains (www.ibm.com, www.ibm.fr) into a single service named IBM using the call.http.host tag.
        Link Calls to an Existing Monitored Service. For example, Link database calls (jdbc:mysql://10.128.0.1:3306) to an existing service like MySQL@3306 on demo-host by referencing its service ID.

        Args:
            id: A unique id of the manual service configuration.
            tagFilterExpression : Boolean expression of tag filters to match relevant calls.
            unmonitoredServiceName : Custom name for an unmonitored service to map. (Optional)
            existingServiceId : Service ID to link the matched calls to. (Optional)
            description: Description of the mapping configuration. (Optional)
            enabled: Enable or disable the configuration. Defaults to True. (Optional)
            ctx: Optional execution context.

        Returns:
            Dict[str, Any]: API response indicating success or failure.
        """
        try:
            debug_print("Creating manual service configuration")

            if not (unmonitoredServiceName and existingServiceId):
                return {
                    "error": "You must provide either 'unmonitoredServiceName' or 'existingServiceId'."
                }
            if not id or not tagFilterExpression:
                return {"error": "Required enitities are missing or invalid"}

            body = {
                "tagFilterExpression": tagFilterExpression,
                "id": id
            }

            if unmonitoredServiceName:
                body["unmonitoredServiceName"] = unmonitoredServiceName
            if existingServiceId:
                body["existingServiceId"] = existingServiceId
            if description:
                body["description"] = description

            manual_service_config = ManualServiceConfig(**body)

            result = api_client.update_manual_service_config(
                id=id,
                manual_service_config=manual_service_config
            )

            if hasattr(result, "to_dict"):
                result_dict = result.to_dict()
            else:
                result_dict = result

            debug_print(f"Manual service configuration result: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error creating manual service configuration: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to create manual service configuration: {e!s}"}


    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def replace_all_manual_service_config(
        self,
        tagFilterExpression: Dict[str, Any],
        unmonitoredServiceName: Optional[str] = None,
        existingServiceId: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = True,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        This tool is used if one wants to update more than 1 manual service configurations.

        There are two use cases on the usage of these APIs:

        Map to an Unmonitored Service with a Custom Name. For example, Map HTTP calls to different Google domains (www.ibm.com, www.ibm.fr) into a single service named IBM using the call.http.host tag.
        Link Calls to an Existing Monitored Service. For example, Link database calls (jdbc:mysql://10.128.0.1:3306) to an existing service like MySQL@3306 on demo-host by referencing its service ID.

        Args:
            id: A unique id of the manual service configuration.
            tagFilterExpression : Boolean expression of tag filters to match relevant calls.
            unmonitoredServiceName : Custom name for an unmonitored service to map. (Optional)
            existingServiceId : Service ID to link the matched calls to. (Optional)
            description: Description of the mapping configuration. (Optional)
            enabled: Enable or disable the configuration. Defaults to True. (Optional)
            ctx: Optional execution context.

        Returns:
            Dict[str, Any]: API response indicating success or failure.
        """
        try:
            debug_print("Creating manual service configuration")

            if not (unmonitoredServiceName and existingServiceId):
                return {
                    "error": "You must provide either 'unmonitoredServiceName' or 'existingServiceId'."
                }
            if not tagFilterExpression:
                return {"error": "Required enitities are missing or invalid"}

            request_body = {}

            if tagFilterExpression:
                request_body["tagFilterExpression"] = {"tagFilterExpression": tagFilterExpression}
            if unmonitoredServiceName:
                request_body["unmonitoredServiceName"] = {"unmonitoredServiceName": unmonitoredServiceName}
            if existingServiceId:
                request_body["existingServiceId"] = {"existingServiceId": existingServiceId}
            if description:
                request_body["description"] = {"description": description}

            new_manual_service_config = NewManualServiceConfig(**request_body)

            result = api_client.replace_all_manual_service_configs(
                new_manual_service_config=new_manual_service_config
            )

            if hasattr(result, "to_dict"):
                result_dict = result.to_dict()
            else:
                result_dict = result

            debug_print(f"Manual service configuration result: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error creating manual service configuration: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to create manual service configuration: {e!s}"}


    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def get_all_service_configs(self,
                             ctx=None,
                             api_client=None) -> List[Dict[str, Any]]:
        """
        This tool gives list of All Service Perspectives Configuration
        Get a list of all Service Perspectives with their configuration settings.
        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            debug_print("Fetching all service configs")
            result = api_client.get_service_configs()
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from get_service_configs: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in get_all_service_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return [{"error": f"Failed to get application data metrics: {e}"}]

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def add_service_configs(self,
                            enabled: bool,
                            match_specification: List[Dict[str, str]],
                            name: str,
                            label:str,
                            id: str,
                            comment: Optional[str] = None,
                            ctx=None,
                            api_client=None) -> List[Dict[str, Any]]:
        """
        This tool gives is used to add new Service Perspectives Configuration
        Get a list of all Service Perspectives with their configuration settings.
        Args:

            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            debug_print("Adding new service config")
            if not (enabled and match_specification and name and label and id):
                return [{"error": "Required entities are missing or invalid"}]

            body = {
                "match_specification": match_specification,
                "enabled": enabled,
                "id": id,
                "label": label,
                "name": name
            }

            if comment:
                body["comment"] = comment

            service_config = ServiceConfig(**body)

            result = api_client.add_service_config(
                service_config=service_config
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from add_service_config: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in add_service_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return [{"error": f"Failed to get application data metrics: {e}"}]

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def replace_all_service_configs(self,
                            enabled: bool,
                            match_specification: List[Dict[str, str]],
                            name: str,
                            label:str,
                            id: str,
                            comment: Optional[str] = None,
                            ctx=None,
                            api_client=None) -> List[Dict[str, Any]]:
        """

        Args:

            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            debug_print("Fetching all service configs")
            if not (enabled or match_specification or name or label or id):
                return [{"error": "Required entities are missing or invalid"}]

            body = {
                "match_specification": match_specification,
                "enabled": enabled,
                "id": id,
                "label": label,
                "name": name
            }

            if comment:
                body["comment"] = comment

            service_config_list = [ServiceConfig(**body)]

            result = api_client.replace_all(
                service_config=service_config_list
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from get_service_configs: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in get_service_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return [{"error": f"Failed to get application data metrics: {e}"}]
    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def order_service_config(self,
                                   request_body: List[str],
                                   ctx=None,
                                   api_client=None) -> Dict[str, Any]:
        """
        order Service Configurations (Custom Service Rules)

        This tool changes the order of service configurations based on the provided list of IDs.
        All service configuration IDs must be included in the request.

        Args:
            request_body: List of service configuration IDs in the desired order.
            ctx: The MCP context (optional)

        Returns:
            A dictionary with the API response or error message.
        """
        try:
            debug_print("ordering service configurations")

            if not request_body:
                return {"error": "The list of service configuration IDs cannot be empty."}

            result = api_client.order_service_config(
                request_body=request_body
            )

            # Convert result to dict if needed
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result

        except Exception as e:
            debug_print(f"Error in order_service_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to order service configs: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def delete_service_config(self,
                                id: str,
                                ctx=None,
                                api_client=None) -> Dict[str, Any]:
        """
        Delete a Service Perspective configuration.
        This tool allows you to delete an existing Service Config by its ID.

        Args:
            id: The ID of the application perspective to delete
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing the result of the deletion or error information
        """
        try:
            if not id:
                return {"error": "Service perspective ID is required for deletion"}


            debug_print(f"Deleting application perspective with ID: {id}")
            # Call the delete_service_config method from the SDK
            api_client.delete_service_config(id=id)

            result_dict = {
                "success": True,
                "message": f"Service Confiuguration '{id}' has been successfully deleted"
            }

            debug_print(f"Successfully deleted service perspective with ID: {id}")
            return result_dict
        except Exception as e:
            debug_print(f"Error in delete_service_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to delete service configuration: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def get_service_config(
        self,
        id: str,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        This MCP tool is used  if one wants to retrieve the particular custom service configuration.
        Args:
            id: An Instana generated unique identifier for a Service.
            ctx: The MCP context (optional)

        Returns:
            Dict[str, Any]: Response from the create/update endpoint configuration API.

        """
        try:
            debug_print("get service config")
            if not id:
                return {"error": "Required entities are missing or invalid"}

            result = api_client.get_service_config(
                id=id
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from get_service_config: {result_dict}")
            return result_dict
        except Exception as e:
            debug_print(f"Error in get_service_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return {"error": f"Failed to get service config: {e!s}"}

    @register_as_tool
    @with_header_auth(ApplicationSettingsApi)
    async def update_service_configs(self,
                            enabled: bool,
                            match_specification: List[Dict[str, str]],
                            name: str,
                            label:str,
                            id: str,
                            comment: Optional[str] = None,
                            ctx=None,
                            api_client=None) -> List[Dict[str, Any]]:
        """
        This tool gives is used if one wants to update a particular custom service rule.
        Args:

            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            debug_print("Adding new service config")
            if not (id and name and label and isinstance(match_specification, list)):
                return [{"error": "Required entities are missing or invalid"}]

            body = {
                "match_specification": match_specification,
                "enabled": enabled,
                "id": id,
                "label": label,
                "name": name
            }

            if comment:
                body["comment"] = comment

            service_config = ServiceConfig(**body)

            result = api_client.put_service_config(
                id=id,
                service_config=service_config
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            debug_print(f"Result from add_service_config: {result_dict}")
            return result_dict

        except Exception as e:
            debug_print(f"Error in add_service_config: {e}")
            traceback.print_exc(file=sys.stderr)
            return [{"error": f"Failed to add new service config: {e!s}"}]
