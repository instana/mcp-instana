"""
Application Settings MCP Tools Module

This module provides application settings-specific MCP tools for Instana monitoring.

The API endpoints of this group provides a way to create, read, update, delete (CRUD) for various configuration settings.
"""

import logging
import re
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastmcp import Context
from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth
from src.prompts import mcp

logger = logging.getLogger(__name__)

# Import the necessary classes from the SDK
try:
    from instana_client.api import (
        ApplicationSettingsApi,  #type: ignore
    )
    from instana_client.api_client import ApiClient  #type: ignore
    from instana_client.configuration import Configuration  #type: ignore
    from instana_client.models import (
        ApplicationConfig,  #type: ignore
        EndpointConfig,  #type: ignore
        ManualServiceConfig,  #type: ignore
        NewApplicationConfig,  #type: ignore
        NewManualServiceConfig,  #type: ignore
        ServiceConfig,  #type: ignore
        TagFilter,  #type: ignore
        TagFilterExpression,  #type: ignore
    )
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

    # CRUD Operations Dispatcher - called by application_smart_router_tool.py
    async def execute_settings_operation(
        self,
        operation: str,
        resource_subtype: str,
        id: Optional[str] = None,
        payload: Optional[Union[Dict[str, Any], str]] = None,
        request_body: Optional[List[str]] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """
        Execute Application Settings CRUD operations.
        Called by the smart router tool.

        Args:
            operation: Operation to perform (get_all, get, create, update, delete, order, replace_all)
            resource_subtype: Type of settings resource (application, endpoint, service, manual_service)
            id: Resource ID (for get, update, delete operations)
            payload: Configuration payload (for create, update operations)
            request_body: List of IDs (for order, replace_all operations)
            ctx: MCP context

        Returns:
            Operation result dictionary
        """
        try:
            # Route based on resource_subtype and operation
            if resource_subtype == "application":
                if operation == "get_all":
                    return await self._get_all_applications_configs(ctx)
                elif operation == "get":
                    return await self._get_application_config(id, ctx)
                elif operation == "create":
                    return await self._add_application_config(payload, ctx)
                elif operation == "update":
                    return await self._update_application_config(id, payload, ctx)
                elif operation == "delete":
                    return await self._delete_application_config(id, ctx)

            elif resource_subtype == "endpoint":
                if operation == "get_all":
                    return await self._get_all_endpoint_configs(ctx)
                elif operation == "get":
                    return await self._get_endpoint_config(id, ctx)
                elif operation == "create":
                    return await self._create_endpoint_config(payload, ctx)
                elif operation == "update":
                    return await self._update_endpoint_config(id, payload, ctx)
                elif operation == "delete":
                    return await self._delete_endpoint_config(id, ctx)

            elif resource_subtype == "service":
                if operation == "get_all":
                    return await self._get_all_service_configs(ctx)
                elif operation == "get":
                    return await self._get_service_config(id, ctx)
                elif operation == "create":
                    return await self._add_service_config(payload, ctx)
                elif operation == "update":
                    return await self._update_service_config(id, payload, ctx)
                elif operation == "delete":
                    return await self._delete_service_config(id, ctx)
                elif operation == "order":
                    return await self._order_service_config(request_body, ctx)
                elif operation == "replace_all":
                    return await self._replace_all_service_configs(payload, ctx)

            elif resource_subtype == "manual_service":
                if operation == "get_all":
                    return await self._get_all_manual_service_configs(ctx)
                elif operation == "create":
                    return await self._add_manual_service_config(payload, ctx)
                elif operation == "update":
                    return await self._update_manual_service_config(id, payload, ctx)
                elif operation == "delete":
                    return await self._delete_manual_service_config(id, ctx)
                elif operation == "replace_all":
                    return await self._replace_all_manual_service_config(payload, ctx)

            return {"error": f"Operation '{operation}' not supported for resource_subtype '{resource_subtype}'"}

        except Exception as e:
            logger.error(f"Error executing {operation} on {resource_subtype}: {e}", exc_info=True)
            return {"error": f"Error executing {operation} on {resource_subtype}: {e!s}"}

    # Individual operation functions

    # @register_as_tool(
    #     title="Get All Applications Configs",
    #     annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    # )
    @with_header_auth(ApplicationSettingsApi)
    async def _get_all_applications_configs(self,
                                           ctx: Optional[Context] = None,
                                           api_client: Any = None) -> List[Dict[str, Any]]:
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
            # Use raw JSON response to avoid Pydantic validation issues
            result = api_client.get_application_configs_without_preload_content()
            import json
            try:
                response_text = result.data.decode('utf-8')
                json_data = json.loads(response_text)
                # Convert to List[Dict[str, Any]] format
                if isinstance(json_data, list):
                    result_dict = json_data
                else:
                    # If it's a single object, wrap it in a list
                    result_dict = [json_data] if json_data else []
                debug_print("Successfully retrieved application configs data")
                return result_dict
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                debug_print(error_message)
                return [{"error": error_message}]

        except Exception as e:
            debug_print(f"Error in get_application_configs: {e}")
            traceback.print_exc(file=sys.stderr)
            return [{"error": f"Failed to get all applications: {e!s}"}]

    def _validate_and_prepare_application_payload(self, payload: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """
        Validate and prepare application configuration payload with proper defaults.

        Returns:
            Dict with either 'payload' (validated) or 'error' and 'missing_fields'
        """
        # Parse the payload if it's a string
        if isinstance(payload, str):
            import json
            try:
                request_body = json.loads(payload)
            except json.JSONDecodeError:
                import ast
                try:
                    request_body = ast.literal_eval(payload)
                except (SyntaxError, ValueError) as e:
                    return {"error": f"Invalid payload format: {e}"}
        else:
            request_body = payload.copy() if payload else {}

        # Define required fields
        required_fields = ['label']
        missing_fields = []

        # Check for required fields
        for field in required_fields:
            if field not in request_body or not request_body[field]:
                missing_fields.append(field)

        if missing_fields:
            return {
                "error": "Missing required fields for application configuration",
                "missing_fields": missing_fields,
                "required_fields": {
                    "label": "Application perspective name (string, required)",
                },
                "optional_fields": {
                    "tagFilterExpression": "Tag filter to match services (dict, optional - defaults to empty EXPRESSION)",
                    "scope": "Monitoring scope (string, optional - defaults to 'INCLUDE_ALL_DOWNSTREAM')",
                    "boundaryScope": "Boundary scope (string, optional - defaults to 'ALL')",
                    "accessRules": "Access control rules (list, optional - defaults to READ_WRITE GLOBAL access)"
                },
                "scope_options": ["INCLUDE_ALL_DOWNSTREAM", "INCLUDE_IMMEDIATE_DOWNSTREAM_DATABASE_AND_MESSAGING", "INCLUDE_NO_DOWNSTREAM"],
                "boundary_scope_options": ["ALL", "INBOUND", "DEFAULT"],
                "access_rules_options": ["READ_WRITE_GLOBAL", "READ_ONLY_GLOBAL", "CUSTOM"],
                "elicitation_prompt": "Please provide the following configuration options:\n1. Scope (INCLUDE_ALL_DOWNSTREAM/INCLUDE_IMMEDIATE_DOWNSTREAM_DATABASE_AND_MESSAGING/INCLUDE_NO_DOWNSTREAM)\n2. Boundary Scope (ALL/INBOUND/DEFAULT)\n3. Access Rules (READ_WRITE_GLOBAL/READ_ONLY_GLOBAL/CUSTOM)\n4. Tag Filter Expression (optional)",
                "example_minimal": {
                    "label": "My Application"
                },
                "example_with_options": {
                    "label": "My Application",
                    "scope": "INCLUDE_ALL_DOWNSTREAM",
                    "boundaryScope": "ALL",
                    "accessRules": [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}],
                    "tagFilterExpression": {
                        "type": "TAG_FILTER",
                        "name": "service.name",
                        "operator": "CONTAINS",
                        "entity": "DESTINATION",
                        "value": "my-service"
                    }
                }
            }

        # Apply defaults for optional fields only if not provided
        if 'scope' not in request_body:
            request_body['scope'] = 'INCLUDE_ALL_DOWNSTREAM'
            debug_print("Applied default scope: INCLUDE_ALL_DOWNSTREAM")

        if 'boundaryScope' not in request_body:
            request_body['boundaryScope'] = 'ALL'
            debug_print("Applied default boundaryScope: ALL")

        if 'accessRules' not in request_body:
            request_body['accessRules'] = [
                {
                    "accessType": "READ_WRITE",
                    "relationType": "GLOBAL"
                }
            ]
            debug_print("Applied default accessRules: READ_WRITE GLOBAL")

        # If no tagFilterExpression provided, use empty EXPRESSION
        if 'tagFilterExpression' not in request_body:
            request_body['tagFilterExpression'] = {
                "type": "EXPRESSION",
                "logicalOperator": "AND",
                "elements": []
            }
            debug_print("Applied default tagFilterExpression: empty EXPRESSION")

        # Convert nested tagFilterExpression to model objects if present
        if 'tagFilterExpression' in request_body and isinstance(request_body['tagFilterExpression'], dict):
            tag_expr = request_body['tagFilterExpression']

            # Handle EXPRESSION type with nested elements
            if tag_expr.get('type') == 'EXPRESSION' and 'elements' in tag_expr:
                converted_elements = []
                for element in tag_expr['elements']:
                    if isinstance(element, dict):
                        element_copy = element.copy()
                        element_copy.pop('value', None)
                        element_copy.pop('key', None)
                        converted_elements.append(TagFilter(**element_copy))
                    else:
                        converted_elements.append(element)
                tag_expr['elements'] = converted_elements
                request_body['tagFilterExpression'] = TagFilterExpression(**tag_expr)

            # Handle TAG_FILTER type (simple filter)
            elif tag_expr.get('type') == 'TAG_FILTER':
                # For TAG_FILTER, ensure both 'value' and 'stringValue' are present
                # Don't convert to TagFilter model - keep as dict to preserve both fields
                tag_filter_copy = tag_expr.copy()
                tag_filter_copy.pop('key', None)
                if 'stringValue' not in tag_filter_copy and 'value' in tag_expr:
                    tag_filter_copy['stringValue'] = tag_expr['value']
                if 'value' not in tag_filter_copy and 'stringValue' in tag_expr:
                    tag_filter_copy['value'] = tag_expr['stringValue']
                # Keep as dictionary - don't convert to TagFilter model
                request_body['tagFilterExpression'] = tag_filter_copy

        return {"payload": request_body}

    @with_header_auth(ApplicationSettingsApi)
    async def _add_application_config(self,
                                      payload: Union[Dict[str, Any], str],
                                      ctx: Optional[Context] = None,
                                      api_client: Any = None) -> Dict[str, Any]:
        """
        Add a new Application Perspective configuration.

        Required fields:
        - label: Application perspective name

        Optional fields (with defaults):
        - tagFilterExpression: Tag filter (defaults to empty EXPRESSION)
        - scope: Monitoring scope (defaults to 'INCLUDE_ALL_DOWNSTREAM')
        - boundaryScope: Boundary scope (defaults to 'ALL')
        - accessRules: Access rules (defaults to READ_WRITE GLOBAL)
        """
        try:
            if not payload:
                return {
                    "error": "payload is required",
                    "required_fields": {
                        "label": "Application perspective name (string, required)"
                    },
                    "example": {
                        "label": "My Application"
                    }
                }

            # Validate and prepare payload with defaults
            validation_result = self._validate_and_prepare_application_payload(payload)

            if "error" in validation_result:
                return validation_result

            request_body = validation_result["payload"]

            # Debug: Log the request body before creating the config object
            debug_print(f"DEBUG: request_body before NewApplicationConfig: {request_body}")

            config_object = NewApplicationConfig(**request_body)

            # Debug: Log what the config object looks like after creation
            if hasattr(config_object, 'to_dict'):
                debug_print(f"DEBUG: config_object.to_dict(): {config_object.to_dict()}")

            result = api_client.add_application_config(new_application_config=config_object)

            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
                # Add helpful information about what was created
                return {
                    **result_dict,
                    "message": f"Application perspective '{request_body.get('label')}' created successfully",
                    "applied_defaults": {
                        "scope": request_body.get('scope'),
                        "boundaryScope": request_body.get('boundaryScope'),
                        "accessRules": "READ_WRITE GLOBAL" if not payload or 'accessRules' not in (payload if isinstance(payload, dict) else {}) else "Custom"
                    }
                }
            return result or {"success": True, "message": "Application config created"}
        except Exception as e:
            logger.error(f"Error in _add_application_config: {e}", exc_info=True)
            return {"error": f"Failed to add application config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _get_application_config(self,
                                      id: str,
                                      ctx: Optional[Context] = None,
                                      api_client: Any = None) -> Dict[str, Any]:
        """
        Get an Application Perspective configuration by ID.

        Note: To get by application name instead of ID, use the smart router tool
        with application_name parameter. The router will automatically resolve
        the name to ID and call this method.

        Args:
            id: Application perspective configuration ID
            ctx: MCP context
            api_client: API client instance

        Returns:
            Application configuration dictionary
        """
        try:
            if not id:
                return {"error": "id is required"}

            result = api_client.get_application_config(id=id)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result
        except Exception as e:
            logger.error(f"Error in _get_application_config: {e}", exc_info=True)
            return {"error": f"Failed to get application config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _update_application_config(self,
                                         id: str,
                                         payload: Union[Dict[str, Any], str],
                                         ctx: Optional[Context] = None,
                                         api_client: Any = None) -> Dict[str, Any]:
        """Update an existing Application Perspective configuration."""
        try:
            if not id or not payload:
                return {"error": "id and payload are required"}

            # Parse the payload if it's a string
            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    try:
                        request_body = ast.literal_eval(payload)
                    except (SyntaxError, ValueError) as e:
                        return {"error": f"Invalid payload format: {e}"}
            else:
                request_body = payload

            # Convert nested tagFilterExpression to model objects if present
            if 'tagFilterExpression' in request_body and isinstance(request_body['tagFilterExpression'], dict):
                tag_expr = request_body['tagFilterExpression']

                # Handle EXPRESSION type with nested elements
                if tag_expr.get('type') == 'EXPRESSION' and 'elements' in tag_expr:
                    converted_elements = []
                    for element in tag_expr['elements']:
                        if isinstance(element, dict):
                            element_copy = element.copy()
                            element_copy.pop('value', None)
                            element_copy.pop('key', None)
                            converted_elements.append(TagFilter(**element_copy))
                        else:
                            converted_elements.append(element)
                    tag_expr['elements'] = converted_elements
                    request_body['tagFilterExpression'] = TagFilterExpression(**tag_expr)

                # Handle TAG_FILTER type (simple filter)
                elif tag_expr.get('type') == 'TAG_FILTER':
                    # For TAG_FILTER, ensure both 'value' and 'stringValue' are present
                    # Don't convert to TagFilter model - keep as dict to preserve both fields
                    tag_filter_copy = tag_expr.copy()
                    tag_filter_copy.pop('key', None)
                    if 'stringValue' not in tag_filter_copy and 'value' in tag_expr:
                        tag_filter_copy['stringValue'] = tag_expr['value']
                    if 'value' not in tag_filter_copy and 'stringValue' in tag_expr:
                        tag_filter_copy['value'] = tag_expr['stringValue']
                    # Keep as dictionary - don't convert to TagFilter model
                    request_body['tagFilterExpression'] = tag_filter_copy

            config_object = ApplicationConfig(**request_body)
            result = api_client.put_application_config(id=id, application_config=config_object)

            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": f"Application config '{id}' updated"}
        except Exception as e:
            logger.error(f"Error in _update_application_config: {e}", exc_info=True)
            return {"error": f"Failed to update application config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _delete_application_config(self,
                                         id: str,
                                         ctx: Optional[Context] = None,
                                         api_client: Any = None) -> Dict[str, Any]:
        """Delete an Application Perspective configuration."""
        try:
            if not id:
                return {"error": "id is required"}

            api_client.delete_application_config(id=id)
            return {"success": True, "message": f"Application config '{id}' deleted successfully"}
        except Exception as e:
            logger.error(f"Error in _delete_application_config: {e}", exc_info=True)
            return {"error": f"Failed to delete application config: {e!s}"}

    # Endpoint Config Operations
    @with_header_auth(ApplicationSettingsApi)
    async def _get_all_endpoint_configs(self,
                                        ctx: Optional[Context] = None,
                                        api_client: Any = None) -> List[Dict[str, Any]]:
        """Get all Endpoint Perspectives Configuration."""
        try:
            result = api_client.get_endpoint_configs_without_preload_content()
            import json
            response_text = result.data.decode('utf-8')
            json_data = json.loads(response_text)
            return json_data if isinstance(json_data, list) else [json_data] if json_data else []
        except Exception as e:
            logger.error(f"Error in _get_all_endpoint_configs: {e}", exc_info=True)
            return [{"error": f"Failed to get endpoint configs: {e!s}"}]

    @with_header_auth(ApplicationSettingsApi)
    async def _get_endpoint_config(self,
                                   id: str,
                                   ctx: Optional[Context] = None,
                                   api_client: Any = None) -> Dict[str, Any]:
        """Get an Endpoint configuration by ID."""
        try:
            if not id:
                return {"error": "id is required"}
            result = api_client.get_endpoint_config(id=id)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result
        except Exception as e:
            logger.error(f"Error in _get_endpoint_config: {e}", exc_info=True)
            return {"error": f"Failed to get endpoint config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _create_endpoint_config(self,
                                      payload: Union[Dict[str, Any], str],
                                      ctx: Optional[Context] = None,
                                      api_client: Any = None) -> Dict[str, Any]:
        """Create or update endpoint configuration for a service."""
        try:
            if not payload:
                return {"error": "payload is required"}

            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            config_object = EndpointConfig(**request_body)
            result = api_client.create_endpoint_config(endpoint_config=config_object)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": "Endpoint config created"}
        except Exception as e:
            logger.error(f"Error in _create_endpoint_config: {e}", exc_info=True)
            return {"error": f"Failed to create endpoint config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _update_endpoint_config(self,
                                      id: str,
                                      payload: Union[Dict[str, Any], str],
                                      ctx: Optional[Context] = None,
                                      api_client: Any = None) -> Dict[str, Any]:
        """Update an endpoint configuration."""
        try:
            if not id or not payload:
                return {"error": "id and payload are required"}

            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            config_object = EndpointConfig(**request_body)
            result = api_client.update_endpoint_config(id=id, endpoint_config=config_object)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": f"Endpoint config '{id}' updated"}
        except Exception as e:
            logger.error(f"Error in _update_endpoint_config: {e}", exc_info=True)
            return {"error": f"Failed to update endpoint config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _delete_endpoint_config(self,
                                      id: str,
                                      ctx: Optional[Context] = None,
                                      api_client: Any = None) -> Dict[str, Any]:
        """Delete an endpoint configuration."""
        try:
            if not id:
                return {"error": "id is required"}
            api_client.delete_endpoint_config(id=id)
            return {"success": True, "message": f"Endpoint config '{id}' deleted successfully"}
        except Exception as e:
            logger.error(f"Error in _delete_endpoint_config: {e}", exc_info=True)
            return {"error": f"Failed to delete endpoint config: {e!s}"}

    # Service Config Operations
    @with_header_auth(ApplicationSettingsApi)
    async def _get_all_service_configs(self,
                                       ctx: Optional[Context] = None,
                                       api_client: Any = None) -> List[Dict[str, Any]]:
        """Get all Service configurations."""
        try:
            result = api_client.get_service_configs_without_preload_content()
            import json
            response_text = result.data.decode('utf-8')
            json_data = json.loads(response_text)
            return json_data if isinstance(json_data, list) else [json_data] if json_data else []
        except Exception as e:
            logger.error(f"Error in _get_all_service_configs: {e}", exc_info=True)
            return [{"error": f"Failed to get service configs: {e!s}"}]

    @with_header_auth(ApplicationSettingsApi)
    async def _get_service_config(self,
                                  id: str,
                                  ctx: Optional[Context] = None,
                                  api_client: Any = None) -> Dict[str, Any]:
        """Get a Service configuration by ID."""
        try:
            if not id:
                return {"error": "id is required"}
            result = api_client.get_service_config(id=id)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result
        except Exception as e:
            logger.error(f"Error in _get_service_config: {e}", exc_info=True)
            return {"error": f"Failed to get service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _add_service_config(self,
                                  payload: Union[Dict[str, Any], str],
                                  ctx: Optional[Context] = None,
                                  api_client: Any = None) -> Dict[str, Any]:
        """Add a new Service configuration."""
        try:
            if not payload:
                return {"error": "payload is required"}

            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            config_object = ServiceConfig(**request_body)
            result = api_client.add_service_config(service_config=config_object)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": "Service config created"}
        except Exception as e:
            logger.error(f"Error in _add_service_config: {e}", exc_info=True)
            return {"error": f"Failed to add service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _update_service_config(self,
                                     id: str,
                                     payload: Union[Dict[str, Any], str],
                                     ctx: Optional[Context] = None,
                                     api_client: Any = None) -> Dict[str, Any]:
        """Update a Service configuration."""
        try:
            if not id or not payload:
                return {"error": "id and payload are required"}

            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            config_object = ServiceConfig(**request_body)
            result = api_client.update_service_config(id=id, service_config=config_object)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": f"Service config '{id}' updated"}
        except Exception as e:
            logger.error(f"Error in _update_service_config: {e}", exc_info=True)
            return {"error": f"Failed to update service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _delete_service_config(self,
                                     id: str,
                                     ctx: Optional[Context] = None,
                                     api_client: Any = None) -> Dict[str, Any]:
        """Delete a Service configuration."""
        try:
            if not id:
                return {"error": "id is required"}
            api_client.delete_service_config(id=id)
            return {"success": True, "message": f"Service config '{id}' deleted successfully"}
        except Exception as e:
            logger.error(f"Error in _delete_service_config: {e}", exc_info=True)
            return {"error": f"Failed to delete service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _order_service_config(self,
                                    request_body: List[str],
                                    ctx: Optional[Context] = None,
                                    api_client: Any = None) -> Dict[str, Any]:
        """Order Service configurations."""
        try:
            if not request_body:
                return {"error": "request_body is required"}
            result = api_client.order_service_config(request_body=request_body)
            return {"success": True, "message": "Service configs ordered successfully", "result": result}
        except Exception as e:
            logger.error(f"Error in _order_service_config: {e}", exc_info=True)
            return {"error": f"Failed to order service configs: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _replace_all_service_configs(self,
                                           payload: Union[Dict[str, Any], str],
                                           ctx: Optional[Context] = None,
                                           api_client: Any = None) -> Dict[str, Any]:
        """Replace all Service configurations."""
        try:
            if not payload:
                return {"error": "payload is required"}

            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            # Assuming request_body is a list of ServiceConfig objects
            config_objects = [ServiceConfig(**item) if isinstance(item, dict) else item for item in request_body]
            result = api_client.replace_all_service_configs(service_config=config_objects)
            return {"success": True, "message": "All service configs replaced successfully", "result": result}
        except Exception as e:
            logger.error(f"Error in _replace_all_service_configs: {e}", exc_info=True)
            return {"error": f"Failed to replace all service configs: {e!s}"}

    # Manual Service Config Operations
    @with_header_auth(ApplicationSettingsApi)
    async def _get_all_manual_service_configs(self,
                                              ctx: Optional[Context] = None,
                                              api_client: Any = None) -> List[Dict[str, Any]]:
        """Get all Manual Service configurations."""
        try:
            result = api_client.get_manual_service_configs_without_preload_content()
            import json
            response_text = result.data.decode('utf-8')
            json_data = json.loads(response_text)
            return json_data if isinstance(json_data, list) else [json_data] if json_data else []
        except Exception as e:
            logger.error(f"Error in _get_all_manual_service_configs: {e}", exc_info=True)
            return [{"error": f"Failed to get manual service configs: {e!s}"}]

    @with_header_auth(ApplicationSettingsApi)
    async def _add_manual_service_config(self,
                                         payload: Union[Dict[str, Any], str],
                                         ctx: Optional[Context] = None,
                                         api_client: Any = None) -> Dict[str, Any]:
        """Add a new Manual Service configuration."""
        try:
            if not payload:
                return {"error": "payload is required"}

            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            config_object = NewManualServiceConfig(**request_body)
            result = api_client.add_manual_service_config(new_manual_service_config=config_object)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": "Manual service config created"}
        except Exception as e:
            logger.error(f"Error in _add_manual_service_config: {e}", exc_info=True)
            return {"error": f"Failed to add manual service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _update_manual_service_config(self,
                                            id: str,
                                            payload: Union[Dict[str, Any], str],
                                            ctx: Optional[Context] = None,
                                            api_client: Any = None) -> Dict[str, Any]:
        """Update a Manual Service configuration."""
        try:
            if not id or not payload:
                return {"error": "id and payload are required"}

            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            config_object = ManualServiceConfig(**request_body)
            result = api_client.update_manual_service_config(id=id, manual_service_config=config_object)
            if hasattr(result, 'to_dict'):
                return result.to_dict()
            return result or {"success": True, "message": f"Manual service config '{id}' updated"}
        except Exception as e:
            logger.error(f"Error in _update_manual_service_config: {e}", exc_info=True)
            return {"error": f"Failed to update manual service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _delete_manual_service_config(self,
                                            id: str,
                                            ctx: Optional[Context] = None,
                                            api_client: Any = None) -> Dict[str, Any]:
        """Delete a Manual Service configuration."""
        try:
            if not id:
                return {"error": "id is required"}
            api_client.delete_manual_service_config(id=id)
            return {"success": True, "message": f"Manual service config '{id}' deleted successfully"}
        except Exception as e:
            logger.error(f"Error in _delete_manual_service_config: {e}", exc_info=True)
            return {"error": f"Failed to delete manual service config: {e!s}"}

    @with_header_auth(ApplicationSettingsApi)
    async def _replace_all_manual_service_config(self,
                                                 payload: Union[Dict[str, Any], str],
                                                 ctx: Optional[Context] = None,
                                                 api_client: Any = None) -> Dict[str, Any]:
        """Replace all Manual Service configurations."""
        try:
            if not payload:
                return {"error": "payload is required"}

            if isinstance(payload, str):
                import json
                try:
                    request_body = json.loads(payload)
                except json.JSONDecodeError:
                    import ast
                    request_body = ast.literal_eval(payload)
            else:
                request_body = payload

            # Assuming request_body is a list of ManualServiceConfig objects
            config_objects = [ManualServiceConfig(**item) if isinstance(item, dict) else item for item in request_body]
            result = api_client.replace_all_manual_service_configs(manual_service_config=config_objects)
            return {"success": True, "message": "All manual service configs replaced successfully", "result": result}
        except Exception as e:
            logger.error(f"Error in _replace_all_manual_service_config: {e}", exc_info=True)
            return {"error": f"Failed to replace all manual service configs: {e!s}"}

