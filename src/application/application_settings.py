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

    @register_as_tool(
        title="Get All Applications Configs",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
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

    @register_as_tool(
        title="Add Application Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def add_application_config(self,
                               payload: Union[Dict[str, Any], str],
                               ctx=None,
                               api_client=None) -> Dict[str, Any]:
        """
        Add a new Application Perspective configuration.
        This tool allows you to create a new Application Perspective with specified settings.
        Sample Payload: {
        "accessRules": [
            {
            "accessType": "READ_WRITE",
            "relationType": "GLOBAL",
            "relatedId": null
            }
        ],
        "boundaryScope": "INBOUND",
        "label": "Discount Build 6987",
        "scope": "INCLUDE_IMMEDIATE_DOWNSTREAM_DATABASE_AND_MESSAGING",
        "tagFilterExpression": {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [
            {
                "type": "TAG_FILTER",
                "name": "kubernetes.label",
                "stringValue": "stage=canary",
                "numberValue": null,
                "booleanValue": null,
                "key": "stage",
                "value": "canary",
                "operator": "EQUALS",
                "entity": "DESTINATION"
            },
            {
                "type": "TAG_FILTER",
                "name": "kubernetes.label",
                "stringValue": "build=6987",
                "numberValue": null,
                "booleanValue": null,
                "key": "build",
                "value": "6987",
                "operator": "EQUALS",
                "entity": "DESTINATION"
            },
            {
                "type": "TAG_FILTER",
                "name": "kubernetes.label",
                "stringValue": "app=discount",
                "numberValue": null,
                "booleanValue": null,
                "key": "app",
                "value": "discount",
                "operator": "EQUALS",
                "entity": "DESTINATION"
            }
            ]
        }
        }
        Returns:
            Dictionary containing the created application perspective configuration or error information
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

            # Import the NewApplicationConfig class
            try:
                from instana_client.models.new_application_config import (
                    NewApplicationConfig,
                )
                logger.debug("Successfully imported NewApplicationConfig")
            except ImportError as e:
                logger.debug(f"Error importing NewApplicationConfig: {e}")
                return {"error": f"Failed to import NewApplicationConfig: {e!s}"}

            # Create an NewApplicationConfig object from the request body
            try:
                logger.debug(f"Creating NewApplicationConfig with params: {request_body}")
                config_object = NewApplicationConfig(**request_body)
                logger.debug("Successfully created config object")
            except Exception as e:
                logger.debug(f"Error creating NewApplicationConfig: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the add_application_config method from the SDK
            logger.debug("Calling add_application_config with config object")
            result = api_client.add_application_config(
                new_application_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Create new application config"
                }

            logger.debug(f"Result from add_application_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in add_application_config: {e}")
            return {"error": f"Failed to add new application config: {e!s}"}

    @register_as_tool(
        title="Delete Application Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
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
            api_client.delete_application_config(id=id)

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

    @register_as_tool(
        title="Get Application Config",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
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

    @register_as_tool(
        title="Update Application Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def update_application_config(
        self,
        id: str,
        payload: Union[Dict[str, Any], str],
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Update an existing Application Perspective configuration.
        This tool allows you to update an existing Application Perspective with specified application Id.

        Args:
            id: The ID of the application perspective to retrieve
            Sample payload: {
        "accessRules": [
            {
            "accessType": "READ",
            "relationType": "ROLE"
            }
        ],
        "boundaryScope": "INBOUND",
        "id": "CxJ55sRbQwqBIfw5DzpRmQ",
        "label": "Discount Build 1",
        "scope": "INCLUDE_NO_DOWNSTREAM",
        "tagFilterExpression": {
            "type": "EXPRESSION",
            "logicalOperator": "AND",
            "elements": [
            {
                "type": "TAG_FILTER",
                "name": "kubernetes.label",
                "stringValue": "stage=canary",
                "numberValue": null,
                "booleanValue": null,
                "key": "stage",
                "value": "canary",
                "operator": "EQUALS",
                "entity": "DESTINATION"
            },
            {
                "type": "TAG_FILTER",
                "name": "kubernetes.label",
                "stringValue": "build=6987",
                "numberValue": null,
                "booleanValue": null,
                "key": "build",
                "value": "6987",
                "operator": "EQUALS",
                "entity": "DESTINATION"
            },
            {
                "type": "TAG_FILTER",
                "name": "kubernetes.label",
                "stringValue": "app=discount",
                "numberValue": null,
                "booleanValue": null,
                "key": "app",
                "value": "discount",
                "operator": "EQUALS",
                "entity": "DESTINATION"
            }
            ]
        }
        }
            ctx: The MCP context (optional)
        Returns:
            Dictionary containing the created application perspective configuration or error information
        """
        try:

            if not payload or not id:
                return {"error": "missing arguments"}

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

            # Import the ApplicationConfig class
            try:
                from instana_client.models.application_config import (
                    ApplicationConfig,
                )
                logger.debug("Successfully imported ApplicationConfig")
            except ImportError as e:
                logger.debug(f"Error importing ApplicationConfig: {e}")
                return {"error": f"Failed to import ApplicationConfig: {e!s}"}

            # Create an ApplicationConfig object from the request body
            try:
                logger.debug(f"Creating ApplicationConfig with params: {request_body}")
                config_object = ApplicationConfig(**request_body)
                logger.debug("Successfully updated application config object")
            except Exception as e:
                logger.debug(f"Error updating ApplicationConfig: {e}")
                return {"error": f"Failed to update config object: {e!s}"}

            # Call the put_application_config method from the SDK
            logger.debug("Calling put_application_config with config object")
            result = api_client.put_application_config(
                id=id,
                application_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Update existing application config"
                }

            logger.debug(f"Result from put_application_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in put_application_config: {e}")
            return {"error": f"Failed to update existing application config: {e!s}"}

    @register_as_tool(
        title="Get All Endpoint Configs",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
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

    @register_as_tool(
        title="Create Endpoint Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def create_endpoint_config(
        self,
        payload: Union[Dict[str, Any], str],
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Create or update endpoint configuration for a service.

        Sample Payload: {
        "serviceId": "d0cedae516f2182ede16f57f67476dd4c7dab9cd",
        "endpointCase": "LOWER",
        "endpointNameByFirstPathSegmentRuleEnabled": false,
        "endpointNameByCollectedPathTemplateRuleEnabled": false,
        "rules": null
        }

        Returns:
            Dict[str, Any]: Response from the create/update endpoint configuration API.
        """
        try:
            if not payload:
                return {"error": "missing arguments"}

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

            # Import the EndpointConfig class
            try:
                from instana_client.models.endpoint_config import (
                    EndpointConfig,
                )
                logger.debug("Successfully imported EndpointConfig")
            except ImportError as e:
                logger.debug(f"Error importing EndpointConfig: {e}")
                return {"error": f"Failed to import EndpointConfig: {e!s}"}

            # Create an EndpointConfig object from the request body
            try:
                logger.debug(f"Creating EndpointConfig with params: {request_body}")
                config_object = EndpointConfig(**request_body)
                logger.debug("Successfully created endpoint config object")
            except Exception as e:
                logger.debug(f"Error creating EndpointConfig: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the create_endpoint_config method from the SDK
            logger.debug("Calling create_endpoint_config with config object")
            result = api_client.create_endpoint_config(
                endpoint_config=config_object
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Create new endpoint config"
                }

            logger.debug(f"Result from create_endpoint_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in create_endpoint_config: {e}")
            return {"error": f"Failed to create new endpoint config: {e!s}"}

    @register_as_tool(
        title="Delete Endpoint Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
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

    @register_as_tool(
        title="Get Endpoint Config",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
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

    @register_as_tool(
        title="Update Endpoint Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def update_endpoint_config(
        self,
        id: str,
        payload: Union[Dict[str, Any], str],
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        update endpoint configuration for a service.

        Args:
            id: An Instana generated unique identifier for a Service.
            {
            "serviceId": "20ba31821b079e7d845a08096124880db3eeeb40",
            "endpointNameByCollectedPathTemplateRuleEnabled": true,
            "endpointNameByFirstPathSegmentRuleEnabled": true,
            "rules": [
                {
                "enabled": true,
                "pathSegments": [
                    {
                    "name": "api",
                    "type": "FIXED"
                    },
                    {
                    "name": "version",
                    "type": "PARAMETER"
                    }
                ],
                "testCases": [
                    "/api/v2/users"
                ]
                }
            ],
            "endpointCase": "UPPER"
            }
            ctx: The MCP context (optional)

        Returns:
            Dict[str, Any]: Response from the create/update endpoint configuration API.
        """
        try:
            if not payload or not id:
                return {"error": "missing arguments"}

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

            # Import the EndpointConfig class
            try:
                from instana_client.models.endpoint_config import (
                    EndpointConfig,
                )
                logger.debug("Successfully imported EndpointConfig")
            except ImportError as e:
                logger.debug(f"Error importing EndpointConfig: {e}")
                return {"error": f"Failed to import EndpointConfig: {e!s}"}

            # Create an EndpointConfig object from the request body
            try:
                logger.debug(f"Creating EndpointConfig with params: {request_body}")
                config_object = EndpointConfig(**request_body)
                logger.debug("Successfully updated endpoint config object")
            except Exception as e:
                logger.debug(f"Error updating EndpointConfig: {e}")
                return {"error": f"Failed to update config object: {e!s}"}

            # Call the update_endpoint_config method from the SDK
            logger.debug("Calling update_endpoint_config with config object")
            result = api_client.update_endpoint_config(
                id=id,
                endpoint_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "update existing endpoint config"
                }

            logger.debug(f"Result from update_endpoint_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in update_endpoint_config: {e}")
            return {"error": f"Failed to update existing application config: {e!s}"}


    @register_as_tool(
        title="Get All Manual Service Configs",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
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

    @register_as_tool(
        title="Add Manual Service Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def add_manual_service_config(
        self,
        payload: Union[Dict[str, Any], str],
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Create a manual service mapping configuration.

        Requires `CanConfigureServiceMapping` permission on the API token.

        Sample payload:
        {
        "description": "Map source service example",
        "enabled": true,
        "existingServiceId": "c467ca0fa21477fee3cde75a140b2963307388a7",
        "tagFilterExpression": {
            "type": "TAG_FILTER",
            "name": "service.name",
            "stringValue": "front",
            "numberValue": null,
            "booleanValue": null,
            "key": null,
            "value": "front",
            "operator": "EQUALS",
            "entity": "SOURCE"
        },
        "unmonitoredServiceName": null
        }
            ctx: Optional execution context.

        Returns:
            Dict[str, Any]: API response indicating success or failure.
        """
        try:
            if not payload:
                return {"error": "missing arguments"}

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

            # Import the NewManualServiceConfig class
            try:
                from instana_client.models.new_manual_service_config import (
                    NewManualServiceConfig,
                )
                logger.debug("Successfully imported NewManualServiceConfig")
            except ImportError as e:
                logger.debug(f"Error importing NewManualServiceConfig: {e}")
                return {"error": f"Failed to import NewManualServiceConfig: {e!s}"}

            # Create an NewManualServiceConfig object from the request body
            try:
                logger.debug(f"Creating NewManualServiceConfig with params: {request_body}")
                config_object = NewManualServiceConfig(**request_body)
                logger.debug("Successfully created manual service config object")
            except Exception as e:
                logger.debug(f"Error creating NewManualServiceConfig: {e}")
                return {"error": f"Failed to create config object: {e!s}"}

            # Call the add_manual_service_config method from the SDK
            logger.debug("Calling add_manual_service_config with config object")
            result = api_client.add_manual_service_config(
                new_manual_service_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Create new manual service config"
                }

            logger.debug(f"Result from add_manual_service_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in add_manual_service_config: {e}")
            return {"error": f"Failed to create new manual service config: {e!s}"}

    @register_as_tool(
        title="Delete Manual Service Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
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

    @register_as_tool(
        title="Update Manual Service Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def update_manual_service_config(
        self,
        id: str,
        payload: Union[Dict[str, Any], str],
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
        Sample payload: {
        "description": "Map source service example",
        "enabled": true,
        "existingServiceId": "c467ca0fa21477fee3cde75a140b2963307388a7",
        "id": "BDGeDcG4TRSzRkJ1mGOk-Q",
        "tagFilterExpression": {
            "type": "TAG_FILTER",
            "name": "service.name",
            "stringValue": "front",
            "numberValue": null,
            "booleanValue": null,
            "key": null,
            "value": "front",
            "operator": "EQUALS",
            "entity": "SOURCE"
        },
        "unmonitoredServiceName": null
        }

        Returns:
            Dict[str, Any]: API response indicating success or failure.
        """
        try:
            if not payload or not id:
                return {"error": "missing arguments"}

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

            # Import the ManualServiceConfig class
            try:
                from instana_client.models.manual_service_config import (
                    ManualServiceConfig,
                )
                logger.debug("Successfully imported ManualServiceConfig")
            except ImportError as e:
                logger.debug(f"Error importing ManualServiceConfig: {e}")
                return {"error": f"Failed to import ManualServiceConfig: {e!s}"}

            # Create an ManualServiceConfig object from the request body
            try:
                logger.debug(f"Creating ManualServiceConfig with params: {request_body}")
                config_object = ManualServiceConfig(**request_body)
                logger.debug("Successfully update manual service config object")
            except Exception as e:
                logger.debug(f"Error creating ManualServiceConfig: {e}")
                return {"error": f"Failed to update manual config object: {e!s}"}

            # Call the update_manual_service_config method from the SDK
            logger.debug("Calling update_manual_service_config with config object")
            result = api_client.update_manual_service_config(
                id=id,
                manual_service_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "update manual service config"
                }

            logger.debug(f"Result from update_manual_service_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in update_manual_service_config: {e}")
            return {"error": f"Failed to update manual config: {e!s}"}


    @register_as_tool(
        title="Replace All Manual Service Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def replace_all_manual_service_config(
        self,
        payload: Union[Dict[str, Any], str],
        ctx=None,
        api_client=None
    ) -> List[Dict[str, Any]]:
        """
        This tool is used if one wants to update more than 1 manual service configurations.

        There are two use cases on the usage of these APIs:

        Map to an Unmonitored Service with a Custom Name. For example, Map HTTP calls to different Google domains (www.ibm.com, www.ibm.fr) into a single service named IBM using the call.http.host tag.
        Link Calls to an Existing Monitored Service. For example, Link database calls (jdbc:mysql://10.128.0.1:3306) to an existing service like MySQL@3306 on demo-host by referencing its service ID.

        Args:
            Sample payload: [
            {
                "description": "Map source service",
                "enabled": true,
                "existingServiceId": "c467ca0fa21477fee3cde75a140b2963307388a7",
                "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "service.name",
                "stringValue": "front",
                "numberValue": null,
                "booleanValue": null,
                "key": null,
                "value": "front",
                "operator": "EQUALS",
                "entity": "SOURCE"
                },
                "unmonitoredServiceName": null
            }
            ]
            ctx: Optional execution context.

        Returns:
            Dict[str, Any]: API response indicating success or failure.
        """
        try:
            if not payload:
                return [{"error": "missing arguments"}]

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
                                return [{"error": f"Invalid payload format: {e2}", "payload": payload}]
                except Exception as e:
                    logger.debug(f"Error parsing payload string: {e}")
                    return [{"error": f"Failed to parse payload: {e}", "payload": payload}]
            else:
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Import the NewManualServiceConfig class
            try:
                from instana_client.models.new_manual_service_config import (
                    NewManualServiceConfig,
                )
                logger.debug("Successfully imported ManualServiceConfig")
            except ImportError as e:
                logger.debug(f"Error importing ManualServiceConfig: {e}")
                return [{"error": f"Failed to import ManualServiceConfig: {e!s}"}]

            # Create an ManualServiceConfig object from the request body
            try:
                logger.debug(f"Creating ManualServiceConfig with params: {request_body}")
                config_object = [NewManualServiceConfig(**request_body)]
                logger.debug("Successfully replace all manual service config object")
            except Exception as e:
                logger.debug(f"Error creating ManualServiceConfig: {e}")
                return [{"error": f"Failed to replace all manual config object: {e!s}"}]

            # Call the replace_all_manual_service_config method from the SDK
            logger.debug("Calling replace_all_manual_service_config with config object")
            result = api_client.replace_all_manual_service_config(
                new_manual_service_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Create replace all manual service config"
                }

            logger.debug(f"Result from replace_all_manual_service_config: {result_dict}")
            return [result_dict]
        except Exception as e:
            logger.error(f"Error in replace_all_manual_service_config: {e}")
            return [{"error": f"Failed to replace all manual config: {e!s}"}]

    @register_as_tool(
        title="Get All Service Configs",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
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

    @register_as_tool(
        title="Add Service Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def add_service_config(self,
                            payload: Union[Dict[str, Any], str],
                            ctx=None,
                            api_client=None) -> Dict[str, Any]:
        """
        This tool gives is used to add new Service Perspectives Configuration
        Get a list of all Service Perspectives with their configuration settings.
        Args:
        {
        "comment": null,
        "enabled": true,
        "label": "{gce.zone}-{jvm.args.abc}",
        "matchSpecification": [
            {
            "key": "gce.zone",
            "value": ".*"
            },
            {
            "key": "jvm.args.abc",
            "value": ".*"
            }
        ],
        "name": "ABC is good"
        }
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            if not payload:
                return {"error": "missing arguments"}

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

            # Import the ServiceConfig class
            try:
                from instana_client.models.service_config import (
                    ServiceConfig,
                )
                logger.debug("Successfully imported ServiceConfig")
            except ImportError as e:
                logger.debug(f"Error importing ServiceConfig: {e}")
                return {"error": f"Failed to import ServiceConfig: {e!s}"}

            # Create an ServiceConfig object from the request body
            try:
                logger.debug(f"Creating ServiceConfig with params: {request_body}")
                config_object = ServiceConfig(**request_body)
                logger.debug("Successfully add service config object")
            except Exception as e:
                logger.debug(f"Error creating ServiceConfig: {e}")
                return {"error": f"Failed to add service config object: {e!s}"}

            # Call the ServiceConfig method from the SDK
            logger.debug("Calling add_service_config with config object")
            result = api_client.add_service_config(
                service_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Create service config"
                }

            logger.debug(f"Result from add_service_config: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in add_service_config: {e}")
            return {"error": f"Failed to add service config: {e!s}"}

    @register_as_tool(
        title="Replace All Service Configs",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def replace_all_service_configs(self,
                            payload: Union[Dict[str, Any], str],
                            ctx=None,
                            api_client=None) -> List[Dict[str, Any]]:
        """
        Args:
            [
            {
                "comment": null,
                "enabled": true,
                "id": "8C-jGYx8Rsue854tzkh8KQ",
                "label": "{docker.container.name}",
                "matchSpecification": [
                {
                    "key": "docker.container.name",
                    "value": ".*"
                }
                ],
                "name": "Rule"
            }
            ]
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            if not payload:
                return [{"error": "missing arguments"}]

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
                                return [{"error": f"Invalid payload format: {e2}", "payload": payload}]
                except Exception as e:
                    logger.debug(f"Error parsing payload string: {e}")
                    return [{"error": f"Failed to parse payload: {e}", "payload": payload}]
            else:
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Import the ServiceConfig class
            try:
                from instana_client.models.service_config import (
                    ServiceConfig,
                )
                logger.debug("Successfully imported ServiceConfig")
            except ImportError as e:
                logger.debug(f"Error importing ServiceConfig: {e}")
                return [{"error": f"Failed to import ServiceConfig: {e!s}"}]

            # Create an ServiceConfig object from the request body
            try:
                logger.debug(f"Creating ServiceConfig with params: {request_body}")
                config_object = [ServiceConfig(**request_body)]
                logger.debug("Successfully replace all manual service config object")
            except Exception as e:
                logger.debug(f"Error creating ServiceConfig: {e}")
                return [{"error": f"Failed to replace all manual config object: {e!s}"}]

            # Call the replace_all method from the SDK
            logger.debug("Calling replace_all with config object")
            result = api_client.replace_all(
                service_config=config_object
            )

            # Convert the result to a list of dictionaries
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "replace all service config"
                }

            logger.debug(f"Result from replace_all: {result_dict}")
            return [result_dict]
        except Exception as e:
            logger.error(f"Error in replace_all: {e}")
            return [{"error": f"Failed to replace all service config: {e!s}"}]


    @register_as_tool(
        title="Order Service Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
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

    @register_as_tool(
        title="Delete Service Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
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

    @register_as_tool(
        title="Get Service Config",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
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

    @register_as_tool(
        title="Update Service Config",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(ApplicationSettingsApi)
    async def update_service_config(self,
                            id: str,
                            payload: Union[Dict[str, Any], str],
                            ctx=None,
                            api_client=None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        This tool gives is used if one wants to update a particular custom service rule.
        Args:
        {
        "comment": null,
        "enabled": true,
        "id": "9uma4MhnTTSyBzwu_FKBJA",
        "label": "{gce.zone}-{jvm.args.abc}",
        "matchSpecification": [
            {
            "key": "gce.zone",
            "value": ".*"
            },
            {
            "key": "jvm.args.abc",
            "value": ".*"
            }
        ],
        "name": "DEF is good"
        }
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            if not payload or not id:
                return [{"error": "missing arguments"}]

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
                                return [{"error": f"Invalid payload format: {e2}", "payload": payload}]
                except Exception as e:
                    logger.debug(f"Error parsing payload string: {e}")
                    return [{"error": f"Failed to parse payload: {e}", "payload": payload}]
            else:
                # If payload is already a dictionary, use it directly
                logger.debug("Using provided payload dictionary")
                request_body = payload

            # Import the ServiceConfig class
            try:
                from instana_client.models.service_config import (
                    ServiceConfig,
                )
                logger.debug("Successfully imported ServiceConfig")
            except ImportError as e:
                logger.debug(f"Error importing ServiceConfig: {e}")
                return [{"error": f"Failed to import ServiceConfig: {e!s}"}]

            # Create an ServiceConfig object from the request body
            try:
                logger.debug(f"Creating ServiceConfig with params: {request_body}")
                config_object = [ServiceConfig(**request_body)]
                logger.debug("Successfully update service config object")
            except Exception as e:
                logger.debug(f"Error creating ServiceConfig: {e}")
                return [{"error": f"Failed to replace all manual config object: {e!s}"}]

            # Call the put_service_config method from the SDK
            logger.debug("Calling put_service_config with config object")
            result = api_client.put_service_config(
                id=id,
                service_config=config_object
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "put service config"
                }

            logger.debug(f"Result from put_service_config: {result_dict}")
            return [result_dict]
        except Exception as e:
            logger.error(f"Error in put_service_config: {e}")
            return [{"error": f"Failed to update service config: {e!s}"}]

