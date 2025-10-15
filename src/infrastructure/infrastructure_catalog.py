"""
Infrastructure Catalog MCP Tools Module

This module provides infrastructure catalog-specific MCP tools for Instana monitoring.
"""

import logging
from typing import Any, Dict, List, Optional

# Import the necessary classes from the SDK
try:
    from instana_client.api.infrastructure_catalog_api import (
        InfrastructureCatalogApi,
    )
    from instana_client.api_client import ApiClient
    from instana_client.configuration import Configuration
except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from mcp.types import ToolAnnotations

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class InfrastructureCatalogMCPTools(BaseInstanaClient):
    """Tools for infrastructure catalog in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Infrastructure Catalog MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Available Payload Keys By Plugin ID",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureCatalogApi)
    async def get_available_payload_keys_by_plugin_id(self,
                                                      plugin_id: str,
                                                      ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get available payload keys for a specific plugin in Instana. This tool retrieves the list of payload keys that can be used to access detailed monitoring data
        for a particular plugin type. Use this when you need to understand what data is available for a specific entity type, want to explore the monitoring capabilities
        for a plugin, or need to find the correct payload key for accessing specific metrics or configuration data. This is particularly useful for preparing detailed
        queries, understanding available monitoring data structures, or when building custom dashboards or integrations. For example, use this tool when asked about
        'what data is available for Java processes', 'payload keys for Kubernetes', 'what metrics can I access for MySQL', or when someone wants to
        'find out what monitoring data is collected for a specific technology'.

        Args:
            plugin_id: The ID of the plugin to get payload keys for
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing payload keys or error information
        """
        try:
            logger.debug(f"get_available_payload_keys_by_plugin_id called with plugin_id={plugin_id}")

            if not plugin_id:
                return {"error": "plugin_id parameter is required"}

            # Try using the standard SDK method
            try:
                # Call the get_available_payload_keys_by_plugin_id method from the SDK
                result = api_client.get_available_payload_keys_by_plugin_id(
                    plugin_id=plugin_id
                )

                # Convert the result to a dictionary
                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict()
                elif isinstance(result, dict):
                    result_dict = result
                elif isinstance(result, list):
                    # Wrap list in a dictionary to match return type
                    items = [item.to_dict() if hasattr(item, 'to_dict') else item for item in result]
                    result_dict = {"payload_keys": items, "plugin_id": plugin_id}
                elif isinstance(result, str):
                    # Handle string response (special case for some plugins like db2Database)
                    logger.debug(f"Received string response for plugin_id={plugin_id}: {result}")
                    result_dict = {"message": result, "plugin_id": plugin_id}
                else:
                    # For any other type, convert to string representation
                    result_dict = {"data": str(result), "plugin_id": plugin_id}

                logger.debug(f"Result from get_available_payload_keys_by_plugin_id: {result_dict}")
                return result_dict

            except Exception as sdk_error:
                logger.error(f"SDK method failed: {sdk_error}, trying fallback")

                # Use the without_preload_content version to get the raw response
                try:
                    response_data = api_client.get_available_payload_keys_by_plugin_id_without_preload_content(
                        plugin_id=plugin_id
                    )

                    # Check if the response was successful
                    if response_data.status != 200:
                        error_message = f"Failed to get payload keys: HTTP {response_data.status}"
                        logger.debug(error_message)
                        return {"error": error_message}

                    # Read the response content
                    response_text = response_data.data.decode('utf-8')

                    # Try to parse as JSON first
                    import json
                    try:
                        result_dict = json.loads(response_text)
                        logger.debug(f"Result from fallback method (JSON): {result_dict}")
                        return result_dict
                    except json.JSONDecodeError:
                        # If not valid JSON, return as string
                        logger.debug(f"Result from fallback method (string): {response_text}")
                        return {"message": response_text, "plugin_id": plugin_id}

                except Exception as fallback_error:
                    logger.warning(f"Fallback method failed: {fallback_error}")
                    raise

        except Exception as e:
            logger.error(f"Error in get_available_payload_keys_by_plugin_id: {e}", exc_info=True)
            return {"error": f"Failed to get payload keys: {e!s}", "plugin_id": plugin_id}


    @register_as_tool(
        title="Get Infrastructure Catalog Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureCatalogApi)
    async def get_infrastructure_catalog_metrics(self,
                                                 plugin: str,
                                                 filter: Optional[str] = None,
                                                 ctx=None, api_client=None) -> List[str]:
        """
        Get metric catalog for a specific plugin in Instana. This tool retrieves all available metric definitions for a requested plugin type.
        Use this when you need to understand what metrics are available for a specific technology, want to explore the monitoring capabilities for a plugin,
        or need to find the correct metric names for queries or dashboards. This is particularly useful for building custom dashboards, setting up alerts based on specific metrics,
        or understanding the monitoring depth for a particular technology. For example, use this tool when asked about 'what metrics are available for hosts',
        'JVM metrics catalog', 'available metrics for Kubernetes', or when someone wants to 'see all metrics for a database'.

        Returns the first 50 metrics to keep the response manageable.

        Args:
            plugin: The plugin ID to get metrics for
            filter: Filter to restrict returned metric definitions ('custom' or 'builtin')
            ctx: The MCP context (optional)

        Returns:
            List of metric names (strings) - limited to first 50 metrics
        """
        try:
            logger.debug(f"get_infrastructure_catalog_metrics called with plugin={plugin}, filter={filter}")

            if not plugin:
                return ["Error: plugin parameter is required"]

            # Call the get_infrastructure_catalog_metrics method from the SDK
            result = api_client.get_infrastructure_catalog_metrics(
                plugin=plugin,
                filter=filter  # Pass the filter parameter to the SDK
            )

            # Handle different response types
            if isinstance(result, list):
                # If it's a list of metric objects or names, extract metric names
                metric_names = []
                for item in result[:50]:  # Limit to first 50
                    if isinstance(item, str):
                        # Already a string (metric name)
                        metric_names.append(item)
                    elif isinstance(item, dict):
                        # Extract metric name from metric object
                        metric_name = item.get('metricId') or item.get('label') or str(item)
                        metric_names.append(metric_name)
                    else:
                        # Convert to string
                        metric_names.append(str(item))

                logger.debug(f"Received {len(result)} metrics for plugin {plugin}, returning first {len(metric_names)}")
                return metric_names

            elif hasattr(result, 'to_dict'):
                # If it's an SDK object with to_dict method
                result_dict = result.to_dict()

                # Check if the dict contains a list of metrics
                if isinstance(result_dict, list):
                    metric_names = []
                    for item in result_dict[:50]:  # Limit to first 50
                        if isinstance(item, str):
                            metric_names.append(item)
                        elif isinstance(item, dict):
                            metric_name = item.get('metricId') or item.get('label') or str(item)
                            metric_names.append(metric_name)
                        else:
                            metric_names.append(str(item))

                    logger.debug(f"Received {len(result_dict)} metrics for plugin {plugin}, returning first {len(metric_names)}")
                    return metric_names
                elif isinstance(result_dict, dict):
                    # Try to extract metric names from dict structure
                    if 'metrics' in result_dict:
                        metrics_list = result_dict['metrics']
                        if isinstance(metrics_list, list):
                            metric_names = []
                            for item in metrics_list[:50]:  # Limit to first 50
                                if isinstance(item, str):
                                    metric_names.append(item)
                                elif isinstance(item, dict):
                                    metric_name = item.get('metricId') or item.get('label') or str(item)
                                    metric_names.append(metric_name)
                                else:
                                    metric_names.append(str(item))
                            return metric_names
                        else:
                            return [f"Metrics field is not a list for plugin {plugin}"]
                    else:
                        return [f"Unexpected dict structure for plugin {plugin}"]
                else:
                    return [f"Unable to parse metrics for plugin {plugin}"]
            else:
                # For any other format
                logger.debug(f"Unexpected result type for plugin {plugin}: {type(result)}")
                return [f"Unexpected response format for plugin {plugin}"]

        except Exception as e:
            logger.error(f"Error in get_infrastructure_catalog_metrics: {e}", exc_info=True)
            return [f"Error: Failed to get metric catalog for plugin '{plugin}': {e!s}"]


    @register_as_tool(
        title="Get Infrastructure Catalog Plugins",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureCatalogApi)
    async def get_infrastructure_catalog_plugins(self, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get plugin catalog from Instana. This tool retrieves all available plugin IDs for your monitored system, showing what types of entities Instana is monitoring in your environment.
        Use this when you need to understand what technologies are being monitored, want to explore the monitoring capabilities of your Instana installation,
        or need to find the correct plugin ID for other API calls. This is particularly useful for discovering what entity types are available for querying,
        understanding your monitoring coverage, or preparing for more detailed data retrieval. For example, use this tool when asked about
        'what technologies are monitored', 'available plugins in Instana', 'list of monitored entity types', or when someone wants to 'see what kinds of systems Instana is tracking'.

        Returns the first 50 plugins to keep the response manageable.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary with plugin list and metadata
        """
        try:
            logger.debug("get_infrastructure_catalog_plugins called")

            # Call the get_infrastructure_catalog_plugins method from the SDK
            result = api_client.get_infrastructure_catalog_plugins()

            # Handle the result based on its type
            if isinstance(result, list):
                # Extract just the plugin IDs from the list of dictionaries
                plugin_ids = []
                for item in result[:50]:  # Limit to first 50 items
                    if isinstance(item, dict) and 'plugin' in item:
                        plugin_ids.append(item['plugin'])
                    elif hasattr(item, 'plugin'):
                        plugin_ids.append(item.plugin)

                logger.debug(f"Extracted {len(plugin_ids)} plugin IDs from response (limited to top 50)")

                # Return structured response that encourages listing
                return {
                    "message": f"Found {len(result)} total plugins. Showing first {len(plugin_ids)} plugins:",
                    "plugins": plugin_ids,
                    "total_available": len(result),
                    "showing": len(plugin_ids),
                    "note": "These are the plugin IDs for different technologies monitored by Instana"
                }

            elif hasattr(result, 'to_dict'):
                # If it's an SDK object with to_dict method
                result_dict = result.to_dict()
                if isinstance(result_dict, list):
                    # Limit to first 50 items
                    limited_result = result_dict[:50]
                    plugin_ids = [item.get('plugin', '') for item in limited_result if isinstance(item, dict)]
                    return {
                        "message": f"Found {len(result_dict)} total plugins. Showing first {len(plugin_ids)} plugins:",
                        "plugins": plugin_ids,
                        "total_available": len(result_dict),
                        "showing": len(plugin_ids)
                    }
                else:
                    return {"error": "Unexpected response format"}
            else:
                # For any other format
                return {"error": "Unable to parse response"}

        except Exception as e:
            logger.error(f"Error in get_infrastructure_catalog_plugins: {e}", exc_info=True)
            return {"error": f"Failed to get plugin catalog: {e!s}"}



    @register_as_tool(
        title="Get Infrastructure Catalog Plugins With Custom Metrics",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureCatalogApi)
    async def get_infrastructure_catalog_plugins_with_custom_metrics(self, ctx=None, api_client=None) -> Dict[str, Any] | List[Dict[str, Any]]:
        """
        Get all plugins with custom metrics catalog from Instana. This tool retrieves information about which entity types (plugins) in your environment have custom metrics configured.
        Use this when you need to identify which technologies have custom monitoring metrics defined, want to explore custom monitoring capabilities,
        or need to find entities with extended metrics beyond the standard set. This is particularly useful for understanding your custom monitoring setup,
        identifying opportunities for additional custom metrics, or troubleshooting issues with custom metric collection. For example, use this tool when asked about 'which systems have custom metrics',
        'custom monitoring configuration', 'plugins with extended metrics', or when someone wants to 'find out where custom metrics are being collected'.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing plugins with custom metrics or error information
        """
        try:
            logger.debug("get_infrastructure_catalog_plugins_with_custom_metrics called")

            # Call the get_infrastructure_catalog_plugins_with_custom_metrics method from the SDK
            result = api_client.get_infrastructure_catalog_plugins_with_custom_metrics()

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, list):
                # Wrap list in a dictionary to match return type
                items = [item.to_dict() if hasattr(item, 'to_dict') else item for item in result]
                result_dict = {"plugins_with_custom_metrics": items}
            else:
                # Ensure we always return a dictionary
                result_dict = result if isinstance(result, dict) else {"data": result}

            logger.debug(f"Result from get_infrastructure_catalog_plugins_with_custom_metrics: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_infrastructure_catalog_plugins_with_custom_metrics: {e}", exc_info=True)
            return {"error": f"Failed to get plugins with custom metrics: {e!s}"}


    @register_as_tool(
        title="Get Tag Catalog",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureCatalogApi)
    async def get_tag_catalog(self, plugin: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get available tags for a particular plugin. This tool retrieves the tag catalog filtered by plugin.

        Args:
            plugin: The plugin name (e.g., 'host', 'jvm', 'openTelemetry')
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing available tags for the plugin or error information
        """
        try:
            logger.debug(f"get_tag_catalog called with plugin={plugin}")

            if not plugin:
                return {"error": "plugin parameter is required"}

            # Try calling the SDK method first
            try:
                # Call the get_tag_catalog method from the SDK
                result = api_client.get_tag_catalog(
                    plugin=plugin
                )

                # Convert the result to a dictionary
                if hasattr(result, 'to_dict'):
                    result_dict = result.to_dict()
                else:
                    # If it's already a dict or another format, use it as is
                    result_dict = result

                logger.debug(f"Result from get_tag_catalog: {result_dict}")
                return result_dict

            except Exception as sdk_error:
                logger.error(f"SDK method failed: {sdk_error}, trying with custom headers")

                # Check if it's a 406 error
                is_406_error = False
                if hasattr(sdk_error, 'status') and sdk_error.status == 406 or "406" in str(sdk_error) and "Not Acceptable" in str(sdk_error):
                    is_406_error = True

                if is_406_error:
                    # Try using the SDK's method with custom headers
                    # The SDK should have a method that allows setting custom headers
                    custom_headers = {
                        "Accept": "*/*"  # More permissive Accept header
                    }

                    # Use the without_preload_content version to get the raw response
                    response_data = api_client.get_tag_catalog_without_preload_content(
                        plugin=plugin,
                        _headers=custom_headers  # Pass custom headers to the SDK method
                    )

                    # Check if the response was successful
                    if response_data.status != 200:
                        error_message = f"Failed to get tag catalog: HTTP {response_data.status}"
                        logger.error(error_message)
                        return {"error": error_message}

                    # Read the response content
                    response_text = response_data.data.decode('utf-8')

                    # Parse the JSON manually
                    import json
                    try:
                        result_dict = json.loads(response_text)
                        logger.debug(f"Result from SDK with custom headers: {result_dict}")
                        return result_dict
                    except json.JSONDecodeError as json_err:
                        error_message = f"Failed to parse JSON response: {json_err}"
                        logger.error(error_message)
                        return {"error": error_message}
                else:
                    # Re-raise if it's not a 406 error
                    raise

        except Exception as e:
            logger.error(f"Error in get_tag_catalog: {e}", exc_info=True)
            return {"error": f"Failed to get tag catalog: {e!s}"}


    @register_as_tool(
        title="Get Tag Catalog All",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureCatalogApi)
    async def get_tag_catalog_all(self, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get all available tags. This tool retrieves the complete list of all tags available in your Instana-monitored environment. It returns every tag across all plugins, services, and technologies, allowing users to explore the full tagging taxonomy.

        Use when the user asks:
        "What tags are available in Instana?"
        "Show me all possible tags I can use for filtering or grouping"
        "What tags exist across all services or technologies?"
        "Give me the complete tag catalog from Instana"

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing a summarized view of available tags or error information
        """
        try:
            logger.debug("get_tag_catalog_all called")

            # Try using the standard SDK method first
            try:
                result = api_client.get_tag_catalog_all()

                # Convert the result to a dictionary
                if hasattr(result, 'to_dict'):
                    full_result = result.to_dict()
                else:
                    # If it's already a dict or another format, use it as is
                    full_result = result

                logger.debug(f"Full result from get_tag_catalog_all (standard method): {full_result}")

                # Create a summarized version of the response
                summarized_result = self._summarize_tag_catalog(full_result)
                return summarized_result

            except Exception as sdk_error:
                logger.error(f"Standard SDK method failed: {sdk_error}, trying fallback")

                # Fallback to using the without_preload_content method
                response_data = api_client.get_tag_catalog_all_without_preload_content()

                # Check if the response was successful
                if response_data.status != 200:
                    error_message = f"Failed to get tag catalog: HTTP {response_data.status}"
                    logger.debug(error_message)

                    if response_data.status in (401, 403):
                        return {"error": "Authentication failed. Please check your API token and permissions."}
                    else:
                        return {"error": error_message}

                # Read the response content
                response_text = response_data.data.decode('utf-8')

                # Parse the JSON manually
                import json
                try:
                    full_result = json.loads(response_text)
                    logger.debug(f"Full result from get_tag_catalog_all (fallback method): {full_result}")

                    # Create a summarized version of the response
                    summarized_result = self._summarize_tag_catalog(full_result)
                    return summarized_result

                except json.JSONDecodeError as json_err:
                    error_message = f"Failed to parse JSON response: {json_err}"
                    logger.error(f"Response text: {response_text}")
                    return {"error": error_message}

        except Exception as e:
            logger.error(f"Error in get_tag_catalog_all: {e}", exc_info=True)
            return {"error": f"Failed to get tag catalog: {e!s}"}

    def _summarize_tag_catalog(self, full_catalog: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summarized version of the tag catalog response that includes tag labels.

        Args:
            full_catalog: The complete tag catalog response

        Returns:
            A simplified version of the tag catalog with tag labels
        """
        summary = {
            "summary": "List of all available tag labels in Instana",
            "categories": {},
            "allLabels": []
        }

        # Extract tag tree if available
        tag_tree = full_catalog.get("tagTree", [])

        # Process each category in the tag tree
        for category in tag_tree:
            category_label = category.get("label", "Uncategorized")
            category_tags = []

            # Process children (actual tags)
            if "children" in category and isinstance(category["children"], list):
                for tag in category["children"]:
                    tag_label = tag.get("label")
                    if tag_label:
                        category_tags.append(tag_label)
                        summary["allLabels"].append(tag_label)

            # Add category to summary if it has tags
            if category_tags:
                summary["categories"][category_label] = sorted(category_tags)

        # Remove duplicates and sort the all labels list
        summary["allLabels"] = sorted(set(summary["allLabels"]))
        summary["count"] = len(summary["allLabels"])

        return summary


    @register_as_tool(
        title="Get Infrastructure Catalog Search Fields",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(InfrastructureCatalogApi)
    async def get_infrastructure_catalog_search_fields(self, ctx=None, api_client=None) -> List[str] | Dict[str, Any]:
        """
        Get search field catalog from Instana. This tool retrieves all available search keywords and fields that can be used in dynamic focus queries for infrastructure monitoring.
        Use this when you need to understand what search criteria are available, want to build complex queries to filter entities, or need to find the correct search syntax for specific entity properties.
        This is particularly useful for constructing advanced search queries, understanding available filtering options, or discovering how to target specific entities in your environment.
        For example, use this tool when asked about 'what search fields are available', 'how to filter hosts by property', 'search syntax for Kubernetes pods', or when someone wants to 'learn how to build complex entity queries'.

        This endpoint retrieves all available search keywords for dynamic focus queries.

        Args:
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing search field keywords or error information
        """
        try:
            logger.debug("get_infrastructure_catalog_search_fields called")

            # Call the get_infrastructure_catalog_search_fields method from the SDK
            result = api_client.get_infrastructure_catalog_search_fields()
            logger.debug(f"API call successful, got {len(result)} search fields")

            # Extract just 10 keywords to keep it very small
            keywords = []

            for field_obj in result[:10]:
                try:
                    if hasattr(field_obj, 'to_dict'):
                        field_dict = field_obj.to_dict()
                        keyword = field_dict.get("keyword", "")
                    else:
                        keyword = getattr(field_obj, 'keyword', "")

                    if keyword:
                        keywords.append(keyword)

                except Exception:
                    continue

            # Wrap the keywords list in a dictionary to match return type
            return {"search_fields": keywords, "count": len(keywords)}

        except Exception as e:
            logger.error(f"Error: {e}")
            return {"error": str(e)}
