"""
Application Resources MCP Tools Module

This module provides application resources-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.types import ToolAnnotations

from src.prompts import mcp

# Import the necessary classes from the SDK
try:
    from instana_client.api.application_resources_api import (
        ApplicationResourcesApi,
    )

except ImportError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class ApplicationResourcesMCPTools(BaseInstanaClient):
    """Tools for application resources in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Application Resources MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool(
        title="Get Application Endpoints",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationResourcesApi)
    async def get_application_endpoints(self,
                                        name_filter: Optional[str] = None,
                                        types: Optional[List[str]] = None,
                                        technologies: Optional[List[str]] = None,
                                        window_size: Optional[int] = None,
                                        to_time: Optional[int] = None,
                                        page: Optional[int] = None,
                                        page_size: Optional[int] = None,
                                        application_boundary_scope: Optional[str] = None,
                                        ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get endpoints for all services from Instana. Use this API endpoint if one wants to retrieve a list of Endpoints. A use case could be to view the endpoint id of an Endpoint.
        Retrieve a list of application endpoints from Instana. This tool is useful when you need to get information about endpoints across services in your application.
        You can filter by endpoint name, types, technologies, and other parameters. Use this when you want to see what endpoints exist in your application, understand their IDs, or analyze endpoint performance metrics.
        For example, use this tool when asked about 'application endpoints', 'service endpoints', 'API endpoints in my application','endpoint id of an Endpoint', or when someone wants to 'list all endpoints'.

        Args:
            name_filter: Name of service to filter by (optional)
            types: List of endpoint types to filter by (optional)
            technologies: List of technologies to filter by (optional)
            window_size: Size of time window in milliseconds (optional)
            to_time: End timestamp in milliseconds (optional)
            page: Page number for pagination (optional)
            page_size: Number of items per page (optional)
            application_boundary_scope: Filter for application scope, e.g., 'INBOUND' or 'ALL' (optional)
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing endpoints data or error information
        """
        try:
            logger.debug(f"get_application_endpoints called with name_filter={name_filter}")

            # Set default time range if not provided
            if not to_time:
                to_time = int(datetime.now().timestamp() * 1000)

            if not window_size:
                window_size = 60 * 60 * 1000  # Default to 1 hour

            # Call the get_application_endpoints method from the SDK
            result = api_client.get_application_endpoints(
                name_filter=name_filter,
                types=types,
                technologies=technologies,
                window_size=window_size,
                to=to_time,
                page=page,
                page_size=page_size,
                application_boundary_scope=application_boundary_scope
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_application_endpoints: {result_dict}")
            return result_dict
        except Exception as e:
            logger.error(f"Error in get_application_endpoints: {e}", exc_info=True)
            return {"error": f"Failed to get application endpoints: {e!s}"}

    @register_as_tool(
        title="Get Application Services",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationResourcesApi)
    async def get_application_services(self,
                                       name_filter: Optional[str] = None,
                                       window_size: Optional[int] = None,
                                       to_time: Optional[int] = None,
                                       page: Optional[int] = None,
                                       page_size: Optional[int] = None,
                                       application_boundary_scope: Optional[str] = None,
                                       include_snapshot_ids: Optional[bool] = None,
                                       ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Retrieve a list of services within application perspectives from Instana. This tool is useful when you need to get information about all services in your monitored applications.
        You can filter by service name and other parameters to narrow down results. Use this when you want to see what services exist in your application,
        understand their IDs, or analyze service-level metrics.   This is particularly helpful when you need to retrieve all service IDs present in an Application Perspective for further analysis or monitoring.
        For example, use this tool when asked about 'application services', 'microservices in my application', 'list all services', or when someone wants to 'get service information'. A use case could be to retrieve all service ids present in an Application Perspective.

        Args:
            name_filter: Name of application/service to filter by (optional)
            window_size: Size of time window in milliseconds (optional)
            to_time: End timestamp in milliseconds (optional)
            page: Page number for pagination (optional)
            page_size: Number of items per page (optional)
            application_boundary_scope: Filter for application scope, e.g., 'INBOUND' or 'ALL' (optional)
            include_snapshot_ids: Whether to include snapshot IDs in the results (optional)
            ctx: The MCP context (optional)

        Returns:
            Dictionary containing service labels with their IDs and summary information
        """
        try:
            logger.debug(f"get_application_services called with name_filter={name_filter}")

            # Set default time range if not provided
            if not to_time:
                to_time = int(datetime.now().timestamp() * 1000)

            if not window_size:
                window_size = 60 * 60 * 1000  # Default to 1 hour

            # Call the get_application_services method from the SDK
            result = api_client.get_application_services(
                name_filter=name_filter,
                window_size=window_size,
                to=to_time,
                page=page,
                page_size=page_size,
                application_boundary_scope=application_boundary_scope,
                include_snapshot_ids=include_snapshot_ids
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_application_services: {result_dict}")

            # Extract service labels and IDs from the items
            services = []
            service_labels = []
            items = result_dict.get('items', [])

            for item in items:
                if isinstance(item, dict):
                    service_id = item.get('id', '')
                    label = item.get('label', '')
                    technologies = item.get('technologies', [])

                    if label and service_id:
                        service_labels.append(label)
                        services.append({
                            'id': service_id,
                            'label': label,
                            'technologies': technologies
                        })
                elif hasattr(item, 'label') and hasattr(item, 'id'):
                    service_labels.append(item.label)
                    services.append({
                        'id': item.id,
                        'label': item.label,
                        'technologies': getattr(item, 'technologies', [])
                    })

            # Sort services by label alphabetically and limit to first 15
            services.sort(key=lambda x: x['label'])
            limited_services = services[:15]
            service_labels = [service['label'] for service in limited_services]

            return {
                "message": f"Found {len(services)} services in application perspectives. Showing first {len(limited_services)}:",
                "service_labels": service_labels,
                "services": limited_services,
                "total_available": len(services),
                "showing": len(limited_services)
            }

        except Exception as e:
            logger.error(f"Error in get_application_services: {e}", exc_info=True)
            return {"error": f"Failed to get application services: {e!s}"}


    @register_as_tool(
        title="Get Applications",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationResourcesApi)
    async def get_applications(self,
                               name_filter: Optional[str] = None,
                               window_size: Optional[int] = None,
                               to_time: Optional[int] = None,
                               page: Optional[int] = None,
                               page_size: Optional[int] = None,
                               application_boundary_scope: Optional[str] = None,
                               ctx=None, api_client=None) -> List[str]:
        """
        Retrieve a list of Application Perspectives from Instana. This tool is useful when you need to get information about any one application perspective in Instana.
        You can filter by application name and other parameters to narrow down results. Use this tool when you want to see what application perspectives exist, understand their IDs,
        or get an overview of your monitored applications. This is particularly helpful when you need to retrieve application IDs for use with other Instana APIs or when setting up monitoring dashboards.
        For example, use this tool when asked about 'application perspectives', 'list all applications in Instana', 'what applications are being monitored', or when someone wants to 'get application IDs'
        or 'get details about an application'.

        Args:
            name_filter: Name of application to filter by (optional)
            window_size: Size of time window in milliseconds (optional)
            to_time: End timestamp in milliseconds (optional)
            page: Page number for pagination (optional)
            page_size: Number of items per page (optional)
            application_boundary_scope: Filter for application scope, e.g., 'INBOUND' or 'ALL' (optional)
            ctx: The MCP context (optional)

        Returns:
            List of application names
        """
        try:
            logger.debug(f"get_applications called with name_filter={name_filter}")

            # Set default time range if not provided
            if not to_time:
                to_time = int(datetime.now().timestamp() * 1000)

            if not window_size:
                window_size = 60 * 60 * 1000  # Default to 1 hour

            # Call the get_applications method from the SDK
            result = api_client.get_applications(
                name_filter=name_filter,
                window_size=window_size,
                to=to_time,
                page=page,
                page_size=page_size,
                application_boundary_scope=application_boundary_scope
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_applications: {result_dict}")

            # Extract labels from the items
            labels = []
            items = result_dict.get('items', [])

            for item in items:
                if isinstance(item, dict):
                    label = item.get('label', '')
                    if label:
                        labels.append(label)
                elif hasattr(item, 'label'):
                    labels.append(item.label)

            # Sort labels alphabetically and limit to first 15
            labels.sort()
            return labels[:15]

        except Exception as e:
            logger.error(f"Error in get_applications: {e}", exc_info=True)
            return [f"Error: Failed to get applications: {e!s}"]


    @register_as_tool(
        title="Get Services",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False)
    )
    @with_header_auth(ApplicationResourcesApi)
    async def get_services(self,
                           name_filter: Optional[str] = None,
                           window_size: Optional[int] = None,
                           to_time: Optional[int] = None,
                           page: Optional[int] = None,
                           page_size: Optional[int] = None,
                           include_snapshot_ids: Optional[bool] = None,
                           ctx=None, api_client=None) -> str:
        """
        Retrieve a list of services from Instana. A use case could be to view the service id, or details,or information of a Service.
        This tool is useful when you need to get information about all services across your monitored environment,regardless of which application perspective they belong to.
        You can filter by service name and other parameters to narrow down results.Use this when you want to see what services exist in your system, understand their IDs .
        This is particularly helpful when you need to retrieve service IDs for further analysis or monitoring. For example, use this tool when asked about 'all services',
        'list services across applications', or when someone wants to 'get service information without application context'. A use case could be to view the service ID of a specific Service.


        Args:
            name_filter: Name of service to filter by (optional)
            window_size: Size of time window in milliseconds (optional)
            to_time: End timestamp in milliseconds (optional)
            page: Page number for pagination (optional)
            page_size: Number of items per page (optional)
            include_snapshot_ids: Whether to include snapshot IDs in the results (optional)
            ctx: The MCP context (optional)

        Returns:
            String containing service names
        """
        try:
            logger.debug(f"get_services called with name_filter={name_filter}")

            # Set default time range if not provided
            if not to_time:
                to_time = int(datetime.now().timestamp() * 1000)

            if not window_size:
                window_size = 60 * 60 * 1000  # Default to 1 hour

            # Call the get_services method from the SDK
            result = api_client.get_services(
                name_filter=name_filter,
                window_size=window_size,
                to=to_time,
                page=page,
                page_size=page_size,
                include_snapshot_ids=include_snapshot_ids
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                # If it's already a dict or another format, use it as is
                result_dict = result

            logger.debug(f"Result from get_services: {result_dict}")

            # Extract labels from the items
            labels = []
            items = result_dict.get('items', [])

            for item in items:
                if isinstance(item, dict):
                    label = item.get('label', '')
                    if label:
                        labels.append(label)
                elif hasattr(item, 'label'):
                    labels.append(item.label)

            # Sort labels alphabetically and limit to first 10
            labels.sort()
            limited_labels = labels[:10]

            # Return as a formatted string that forces display
            services_text = "Services found in your environment:\n"
            for i, label in enumerate(limited_labels, 1):
                services_text += f"{i}. {label}\n"

            services_text += f"\nShowing {len(limited_labels)} out of {len(labels)} total services."

            return services_text

        except Exception as e:
            logger.error(f"Error in get_services: {e}", exc_info=True)
            return f"Error: Failed to get services: {e!s}"
