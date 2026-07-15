"""
Application Resources MCP Tools Module

This module provides application resources-specific MCP tools for Instana monitoring.
"""

import logging
import json
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

    # CRUD Operations Dispatcher - called by application_smart_router_tool.py
    async def execute_resources_operation(
        self,
        operation: str,
        application_id: Optional[str] = None,
        service_id: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        name_filter: Optional[str] = None,
        types: Optional[List[str]] = None,
        technologies: Optional[List[str]] = None,
        application_boundary_scope: Optional[str] = None,
        include_snapshot_ids: Optional[bool] = None,
        ctx=None
    ) -> Dict[str, Any]:
        """
        Execute Application Resources operations.
        Called by the smart router tool.

        Args:
            operation: Operation to perform (get_applications, get_services, get_application_services, get_application_endpoints)
            application_id: Application ID
            service_id: Service ID
            endpoint_id: Endpoint ID
            name_filter: Name filter for searching
            types: List of endpoint types to filter
            technologies: List of technologies to filter
            application_boundary_scope: Application boundary scope
            include_snapshot_ids: Whether to include snapshot IDs
            ctx: MCP context

        Returns:
            Operation result dictionary with paginated results
        """
        try:
            if operation == "get_applications":
                return await self.get_applications(
                    name_filter=name_filter,
                    application_boundary_scope=application_boundary_scope,
                    ctx=ctx
                )
            elif operation == "get_services":
                return await self.get_services(
                    name_filter=name_filter,
                    include_snapshot_ids=include_snapshot_ids,
                    ctx=ctx
                )
            elif operation == "get_application_services":
                return await self.get_application_services(
                    application_id=application_id,
                    service_id=service_id,
                    name_filter=name_filter,
                    application_boundary_scope=application_boundary_scope,
                    include_snapshot_ids=include_snapshot_ids,
                    ctx=ctx
                )
            elif operation == "get_application_endpoints":
                return await self.get_application_endpoints(
                    application_id=application_id,
                    service_id=service_id,
                    endpoint_id=endpoint_id,
                    name_filter=name_filter,
                    types=types,
                    technologies=technologies,
                    application_boundary_scope=application_boundary_scope,
                    ctx=ctx
                )
            else:
                return {"error": f"Operation '{operation}' not supported"}

        except Exception as e:
            logger.error(f"Error executing {operation}: {e}", exc_info=True)
            return {"error": f"Error executing {operation}: {e!s}"}

    @with_header_auth(ApplicationResourcesApi)
    async def _get_applications_internal(
        self,
        name_filter: Optional[str] = None,
        window_size: Optional[int] = None,
        to_time: Optional[int] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        application_boundary_scope: Optional[str] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Internal method to get applications from Application Resources API.
        Used by smart router for application name resolution.

        Args:
            name_filter: Name of application to filter by
            window_size: Size of time window in milliseconds
            to_time: End timestamp in milliseconds
            page: Pagination page number
            page_size: Pagination page size
            application_boundary_scope: Application boundary scope
            ctx: The MCP context
            api_client: API client (injected by decorator)

        Returns:
            Dictionary containing applications data
        """
        try:
            logger.debug(f"_get_applications_internal called with name_filter={name_filter}")

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
                result_dict = result

            logger.debug(f"Result from _get_applications_internal: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in _get_applications_internal: {e}", exc_info=True)
            return {"error": f"Failed to get applications: {e!s}"}

    @with_header_auth(ApplicationResourcesApi)
    async def get_application_endpoints(
        self,
        application_id: Optional[str] = None,
        service_id: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        name_filter: Optional[str] = None,
        types: Optional[List[str]] = None,
        technologies: Optional[List[str]] = None,
        application_boundary_scope: Optional[str] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get endpoints for an application service.
        
        Returns paginated results automatically from the API.
        """
        try:
            logger.debug(
                f"get_application_endpoints called with application_id={application_id}, service_id={service_id}, endpoint_id={endpoint_id}"
            )

            # SDK incorrectly marks application_id, service_id, and endpoint_id as required,
            # but they're optional for listing endpoints. Use empty strings as defaults
            # when parameters are None to bypass SDK validation
            if application_id is None:
                application_id = ""
            if service_id is None:
                service_id = ""
            if endpoint_id is None:
                endpoint_id = ""

            # Use _without_preload_content to avoid SDK validation issues
            response = api_client.get_application_endpoints_without_preload_content(
                application_id=application_id,
                service_id=service_id,
                endpoint_id=endpoint_id,
                name_filter=name_filter,
                types=types,
                technologies=technologies,
                application_boundary_scope=application_boundary_scope,
            )

            # Parse the raw JSON response
            result_dict = json.loads(response.data.decode('utf-8'))

            logger.debug(f"Result from get_application_endpoints: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_application_endpoints: {e}", exc_info=True)
            return {"error": f"Failed to get application endpoints: {e!s}"}

    def _sanitize_items_technologies(self, result_dict: Dict[str, Any]) -> None:
        """Sanitize technologies field in items to ensure it's always a list."""
        if not isinstance(result_dict, dict) or 'items' not in result_dict:
            return
        
        items = result_dict.get('items', [])
        if not isinstance(items, list):
            return
        
        for item in items:
            if isinstance(item, dict) and item.get('technologies') is None:
                item['technologies'] = []

    @with_header_auth(ApplicationResourcesApi)
    async def get_application_services(
        self,
        application_id: Optional[str] = None,
        service_id: Optional[str] = None,
        name_filter: Optional[str] = None,
        application_boundary_scope: Optional[str] = None,
        include_snapshot_ids: Optional[bool] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get services for an application perspective.
        
        Returns paginated results automatically from the API.
        """
        try:
            logger.debug(
                f"get_application_services called with application_id={application_id}, service_id={service_id}"
            )

            # SDK incorrectly marks service_id as required, but it's optional for listing all services
            # Use empty string as default when service_id is None to bypass SDK validation
            if service_id is None:
                service_id = ""

            # Use _without_preload_content to avoid SDK validation issues
            response = api_client.get_application_services_without_preload_content(
                application_id=application_id,
                service_id=service_id,
                name_filter=name_filter,
                application_boundary_scope=application_boundary_scope,
                include_snapshot_ids=include_snapshot_ids,
            )

            # Parse the raw JSON response
            result_dict = json.loads(response.data.decode('utf-8'))
            self._sanitize_items_technologies(result_dict)

            logger.debug(f"Result from get_application_services: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_application_services: {e}", exc_info=True)
            return {"error": f"Failed to get application services: {e!s}"}

    @with_header_auth(ApplicationResourcesApi)
    async def get_applications(
        self,
        name_filter: Optional[str] = None,
        application_boundary_scope: Optional[str] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get application perspectives.
        
        Returns paginated results automatically from the API.
        """
        try:
            logger.debug(f"get_applications called with name_filter={name_filter}")

            # Call the get_applications method from the SDK without time/pagination params
            result = api_client.get_applications(
                name_filter=name_filter,
                application_boundary_scope=application_boundary_scope
            )

            # Convert the result to a dictionary
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result

            logger.debug(f"Result from get_applications: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_applications: {e}", exc_info=True)
            return {"error": f"Failed to get applications: {e!s}"}

    @with_header_auth(ApplicationResourcesApi)
    async def get_services(
        self,
        name_filter: Optional[str] = None,
        include_snapshot_ids: Optional[bool] = None,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        Get services for application monitoring.
        
        Returns paginated results automatically from the API.
        """
        try:
            logger.debug(f"get_services called with name_filter={name_filter}")

            response = api_client.get_services_without_preload_content(
                name_filter=name_filter,
                include_snapshot_ids=include_snapshot_ids,
            )

            # Parse the raw JSON response
            result_dict = json.loads(response.data.decode('utf-8'))
            self._sanitize_items_technologies(result_dict)

            logger.debug(f"Result from get_services: {result_dict}")
            return result_dict

        except Exception as e:
            logger.error(f"Error in get_services: {e}", exc_info=True)
            return {"error": f"Failed to get services: {e!s}"}