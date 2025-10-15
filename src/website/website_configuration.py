"""
Website Configuration MCP Tools Module

This module provides website configuration-specific MCP tools for Instana monitoring.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Import the necessary classes from the SDK
try:
    from instana_client.api.website_configuration_api import WebsiteConfigurationApi
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class WebsiteConfigurationMCPTools(BaseInstanaClient):
    """Tools for website configuration in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Website Configuration MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Websites",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def get_websites(self, ctx=None, api_client=None) -> List[Dict[str, Any]]:
        """
        Get all websites.

        This API endpoint retrieves all configured websites in your Instana environment.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing websites data or error information
        """
        try:
            logger.debug("get_websites called")

            # Call the get_websites method from the SDK
            result = api_client.get_websites()

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_websites: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_websites: {e}", exc_info=True)
            return [{"error": f"Failed to get websites: {e!s}"}]

    @register_as_tool(
        title="Get Website",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def get_website(self, website_id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get a specific website by ID.

        This API endpoint retrieves configuration details for a specific website.

        Args:
            website_id: ID of the website to retrieve
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing website data or error information
        """
        try:
            logger.debug(f"get_website called with website_id={website_id}")

            # Call the get_website method from the SDK
            result = api_client.get_website(website_id=website_id)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_website: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_website: {e}", exc_info=True)
            return {"error": f"Failed to get website: {e!s}"}

    @register_as_tool(
        title="Create Website",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def create_website(self,
                            name: str,
                            payload: Optional[Dict[str, Any]] = None,
                            ctx=None,
                            api_client=None) -> Dict[str, Any]:
        """
        Create a new website configuration.

        This API endpoint creates a new website configuration in your Instana environment.

        Args:
            name: Name of the website
            payload: Website configuration payload as a dictionary or JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing created website data or error information
        """
        try:
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

            # Create an Website object from the request body
            try:
                query_params = {}
                if request_body and "display_name" in request_body:
                    query_params["display_name"] = request_body["display_name"]
                if request_body and "id" in request_body:
                    query_params["id"] = request_body["id"]
                logger.debug(f"Creating Website with params: {query_params}")
            except Exception as e:
                logger.debug(f"Error creating create_website: {e}")
                return {"error": f"Failed to create website: {e!s}"}

            # Call the create_website method from the SDK
            logger.debug("Calling create_website with config object")
            result = api_client.create_website(
                name=name
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Create website"
                }

            logger.debug(f"Result from create_website: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in create_website: {e}")
            return {"error": f"Failed to create website: {e!s}"}

    @register_as_tool(
        title="Delete Website",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def delete_website(self, website_id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Delete a website configuration.

        This API endpoint deletes a website configuration from your Instana environment.

        Args:
            website_id: ID of the website to delete
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing deletion result or error information
        """
        try:
            logger.debug(f"delete_website called with website_id={website_id}")

            # Call the delete_website method from the SDK
            api_client.delete_website(website_id=website_id)

            logger.debug("Website deleted successfully")
            return {"success": True, "message": f"Website {website_id} deleted successfully"}
        except Exception as e:
            logger.error(f"Error in delete_website: {e}", exc_info=True)
            return {"error": f"Failed to delete website: {e!s}"}

    @register_as_tool(
        title="Rename Website",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def rename_website(self,
                            website_id: str,
                            name: Optional[str] = None,
                            ctx=None,
                            api_client=None) -> Dict[str, Any]:
        """
        Rename a website configuration.

        This API endpoint renames a website configuration in your Instana environment.

        Args:
            website_id: ID of the website to rename
            name: New name for the website
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing rename result or error information
        """

        try:
            logger.debug(f"rename_website called with website_id={website_id}")

            if not website_id:
                return {"error": "website_id parameter is required"}

            # Call the rename_website method from the SDK
            result = api_client.rename_website(website_id=website_id,name=name)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from rename_website: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in rename_website: {e}", exc_info=True)
            return {"error": f"Failed to rename website: {e!s}"}

    @register_as_tool(
        title="Get Website Geo Location Configuration",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def get_website_geo_location_configuration(self,
                                                    website_id: str,
                                                    ctx=None,
                                                    api_client=None) -> Dict[str, Any]:
        """
        Get geo-location configuration for a website.

        This API endpoint retrieves geo-location configuration for a specific website.

        Args:
            website_id: ID of the website
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing geo-location configuration or error information
        """
        try:
            logger.debug(f"get_website_geo_location_configuration called with website_id={website_id}")

            # Call the get_website_geo_location_configuration method from the SDK
            result = api_client.get_website_geo_location_configuration(website_id=website_id)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_website_geo_location_configuration: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_website_geo_location_configuration: {e}", exc_info=True)
            return {"error": f"Failed to get website geo-location configuration: {e!s}"}

    @register_as_tool(
        title="Update Website Geo Location Configuration",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def update_website_geo_location_configuration(self,
                                                        website_id: str,
                                                        payload: Union[Dict[str, Any], str],
                                                        ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Update geo-location configuration for a website.

        This API endpoint updates geo-location configuration for a specific website.

        Args:
            website_id: ID of the website
            payload: Geo-location configuration payload as a dictionary or JSON string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing updated configuration or error information
        """
        try:
            logger.debug("update_website_geo_location_configuration called")

            # Parse the payload
            if isinstance(payload, str):
                logger.debug("payload is a string, attempting to parse")
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

            try:
                from instana_client.models.geo_location_configuration import (
                    GeoLocationConfiguration,
                )
                logger.debug("Successfully imported GeoLocationConfiguration")
            except ImportError as e:
                logger.debug(f"Error importing GeoLocationConfiguration: {e}")
                return {"error": f"Failed to import GeoLocationConfiguration: {e!s}"}

            # Create an GeoLocationConfiguration object from the request body
            try:
                query_params = {}

                # Required field: geo_detail_removal (with alias geoDetailRemoval)
                # Always provide a default value to ensure the required field is present
                query_params["geo_detail_removal"] = "NO_REMOVAL"  # Default value

                if request_body:
                    if "geoDetailRemoval" in request_body:
                        query_params["geo_detail_removal"] = request_body["geoDetailRemoval"]
                    elif "geo_detail_removal" in request_body:
                        query_params["geo_detail_removal"] = request_body["geo_detail_removal"]

                    # Optional field: geo_mapping_rules
                    if "geoMappingRules" in request_body:
                        query_params["geo_mapping_rules"] = request_body["geoMappingRules"]
                    elif "geo_mapping_rules" in request_body:
                        query_params["geo_mapping_rules"] = request_body["geo_mapping_rules"]

                logger.debug(f"Creating GeoLocationConfiguration with params: {query_params}")
                config_object = GeoLocationConfiguration(**query_params)
                logger.debug("Successfully created GeoLocationConfiguration object")
            except Exception as e:
                logger.debug(f"Error creating GeoLocationConfiguration: {e}")
                return {"error": f"Failed to create GeoLocationConfiguration: {e!s}"}

            # Call the update_website_geo_location_configuration method from the SDK
            logger.debug("Calling update_website_geo_location_configuration with config object")
            result = api_client.update_website_geo_location_configuration(
                website_id=website_id,
                geo_location_configuration=config_object,
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Update website geo-location configuration"
                }

            logger.debug(f"Result from update_website_geo_location_configuration: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in update_website_geo_location_configuration: {e}")
            return {"error": f"Failed to update website geo-location configuration: {e!s}"}

    @register_as_tool(
        title="Get Website IP Masking Configuration",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def get_website_ip_masking_configuration(self, website_id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get IP masking configuration for a website.

        This API endpoint retrieves IP masking configuration for a specific website.

        Args:
            website_id: ID of the website
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing IP masking configuration or error information
        """
        try:
            logger.debug(f"get_website_ip_masking_configuration called with website_id={website_id}")

            # Call the get_website_ip_masking_configuration method from the SDK
            result = api_client.get_website_ip_masking_configuration(website_id=website_id)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_website_ip_masking_configuration: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_website_ip_masking_configuration: {e}", exc_info=True)
            return {"error": f"Failed to get website IP masking configuration: {e!s}"}

    @register_as_tool(
        title="Update Website IP Masking Configuration",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def update_website_ip_masking_configuration(self,
                                                        website_id: str,
                                                        payload: Optional[Dict[str, Any]] = None,
                                                        ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Update IP masking configuration for a website.

        This API endpoint updates IP masking configuration for a specific website.

        Args:
            website_id: ID of the website
            payload: IP masking configuration payload as a dictionary or JSON string
            {
                "ipMasking": "DEFAULT"
            }
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing updated configuration or error information
        """
        try:
            logger.debug("update_website_geo_location_configuration called")

            # Parse the payload
            if isinstance(payload, str):
                logger.debug("payload is a string, attempting to parse")
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

            try:
                from instana_client.models.ip_masking_configuration import (
                    IpMaskingConfiguration,
                )
                logger.debug("Successfully imported IpMaskingConfiguration")
            except ImportError as e:
                logger.debug(f"Error importing IpMaskingConfiguration: {e}")
                return {"error": f"Failed to import IpMaskingConfiguration: {e!s}"}

            # Create an IpMaskingConfiguration object from the request body
            try:
                query_params = {}

                # Required field: ip_masking (with alias ipMasking)
                # Always provide a default value to ensure the required field is present
                query_params["ip_masking"] = "DEFAULT"  # Default value

                if request_body:
                    if "ipMasking" in request_body:
                        query_params["ip_masking"] = request_body["ipMasking"]
                    elif "ip_masking" in request_body:
                        query_params["ip_masking"] = request_body["ip_masking"]

                logger.debug(f"Creating IpMaskingConfiguration with params: {query_params}")
                config_object = IpMaskingConfiguration(**query_params)
                logger.debug("Successfully created IpMaskingConfiguration object")
            except Exception as e:
                logger.debug(f"Error creating IpMaskingConfiguration: {e}")
                return {"error": f"Failed to create IpMaskingConfiguration: {e!s}"}

            # Call the update_website_geo_location_configuration method from the SDK
            logger.debug("Calling update_website_ip_masking_configuration with config object")
            result = api_client.update_website_ip_masking_configuration(
                website_id=website_id,
                ip_masking_configuration=config_object,
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Update website ip-masking configuration"
                }

            logger.debug(f"Result from update_website_ip_masking_configuration: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in update_website_ip_masking_configuration: {e}")
            return {"error": f"Failed to update website ip-masking configuration: {e!s}"}

    @register_as_tool(
        title="Get Website Geo Mapping Rules",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def get_website_geo_mapping_rules(self, website_id: str, ctx=None, api_client=None) -> List[Dict[str, Any]]:
        """
       Get custom geo mapping rules for website

        This API endpoint retrieves custom geo mapping rules for a specific website.

        Args:
            website_id: ID of the website
            ctx: The MCP context (optional)

        Returns:
            List containing custom geo mapping rules or error information
        """
        try:
            logger.debug(f"get_website_geo_mapping_rules called with website_id={website_id}")

            # Call the get_website_geo_mapping_rules method from the SDK
            # Use the raw response method to get the actual CSV data
            try:
                result = api_client.get_website_geo_mapping_rules(website_id=website_id)

                # If the high-level method returns None, try the raw response
                if result is None:
                    response = api_client.get_website_geo_mapping_rules_without_preload_content(website_id=website_id)
                    # Get the raw response data
                    if hasattr(response, 'data'):
                        csv_data = response.data.decode('utf-8') if isinstance(response.data, bytes) else str(response.data)
                    else:
                        csv_data = str(response)
                else:
                    csv_data = str(result)

            except Exception as api_error:
                logger.warning(f"High-level API call failed: {api_error}, trying raw response")
                # Fallback to raw HTTP response
                response = api_client.get_website_geo_mapping_rules_without_preload_content(website_id=website_id)
                if hasattr(response, 'data'):
                    csv_data = response.data.decode('utf-8') if isinstance(response.data, bytes) else str(response.data)
                else:
                    csv_data = str(response)

            # Handle CSV response format
            result_list: List[Dict[str, Any]] = []

            if csv_data and ',' in csv_data:
                # Parse CSV response
                import csv
                import io

                csv_reader = csv.DictReader(io.StringIO(csv_data))
                for row in csv_reader:
                    result_list.append(dict(row))
            elif csv_data:
                # If it's not CSV but has data, return as single item
                result_list.append({"data": csv_data})

            logger.debug(f"Result from get_website_geo_mapping_rules: {result_list}")
            return result_list
        except Exception as e:
            logger.error(f"Error in get_website_geo_mapping_rules: {e}", exc_info=True)
            return [{"error": f"Failed to get website geo mapping rules: {e!s}"}]

    @register_as_tool(
        title="Set Website Geo Mapping Rules",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def set_website_geo_mapping_rules(self,
                                            website_id: str,
                                            body: Optional[str] = None,
                                            ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Set custom geo mapping rules for website

        This API endpoint sets custom geo mapping rules for a specific website.

        Args:
            website_id: ID of the website
            body: Geo mapping rules payload as a string
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing custom geo mapping rules or error information
        """
        try:
            logger.debug(f"set_website_geo_mapping_rules called with website_id={website_id}")

            if not website_id:
                return {"error": "website_id parameter is required"}

            # Call the set_website_geo_mapping_rules method from the SDK
            # The API automatically sets content-type to text/csv
            result = api_client.set_website_geo_mapping_rules(
                website_id=website_id,
                body=body
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from set_website_geo_mapping_rules: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in set_website_geo_mapping_rules: {e}", exc_info=True)
            return {"error": f"Failed to set website geo mapping rules: {e!s}"}

    @register_as_tool(
        title="Upload Source Map File",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def upload_source_map_file(self,
                                        website_id: str,
                                        source_map_config_id: str,
                                        file_format: Optional[str] = None,
                                        source_map: Optional[str] = None,
                                        url: Optional[str] = None,
                                        ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Upload source map file for a website.

        This API endpoint uploads a source map file for a specific website.

        Args:
            website_id: ID of the website
            source_map_config_id: ID of the source map config
            file_format: Format of the source map file
            source_map: Source map file
            url: URL of the source map file
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing updated configuration or error information
        """
        try:
            if not website_id:
                return {"error": "website_id parameter is required"}
            if not source_map_config_id:
                return {"error": "source_map_config_id parameter is required"}

            logger.debug("upload_source_map_file called")

            # Call the upload_source_map_file method from the SDK
            logger.debug("Calling upload_source_map_file with config object")
            result = api_client.upload_source_map_file(
                website_id=website_id,
                source_map_config_id=source_map_config_id,
                file_format=file_format,
                source_map=source_map,
                url=url,
            )
            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result or {
                    "success": True,
                    "message": "Upload source map file"
                }

            logger.debug(f"Result from upload_source_map_file: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in upload_source_map_file: {e}")
            return {"error": f"Failed to upload source map file: {e!s}"}

    @register_as_tool(
        title="Clear Source Map Upload Configuration",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False)
    )
    @with_header_auth(WebsiteConfigurationApi)
    async def clear_source_map_upload_configuration(self,
                                                    website_id: str,
                                                    source_map_config_id: str,
                                                    ctx=None, api_client=None) -> Dict[str, Any]:
        """
       Clear source map upload configuration for a website.

        This API endpoint clears source map upload configuration for a specific website.

        Args:
            website_id: ID of the website
            source_map_config_id: ID of the source map config
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing source map upload configuration or error information
        """
        try:
            if not website_id:
                return {"error": "website_id parameter is required"}
            if not source_map_config_id:
                return {"error": "source_map_config_id parameter is required"}

            logger.debug(f"clear_source_map_upload_configuration called with website_id={website_id} and source_map_config_id={source_map_config_id}")

            # Call the clear_source_map_upload_configuration method from the SDK
            result = api_client.clear_source_map_upload_configuration(
                website_id=website_id,
                source_map_config_id=source_map_config_id)

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from clear_source_map_upload_configuration: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in clear_source_map_upload_configuration: {e}", exc_info=True)
            return {"error": f"Failed to clear source map upload configuration: {e!s}"}


