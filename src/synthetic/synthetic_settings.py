"""
Synthetic Settings MCP Tools Module

This module provides synthetic settings-specific MCP tools for Instana monitoring.
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import the necessary classes from the SDK
try:
    from instana_client.api.synthetic_settings_api import SyntheticSettingsApi
except ImportError as e:
    logger.error("Error importing Instana SDK: %s", e, exc_info=True)
    raise

from src.core.utils import (
    BaseInstanaClient,
    call_sdk_fn,
    decode_response,
    sdk_call_with_keepalive,
    with_header_auth,
)


class SyntheticSettingsMCPTools(BaseInstanaClient):
    """Tools for synthetic settings in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Synthetic Settings MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @with_header_auth(SyntheticSettingsApi)
    async def get_synthetic_test(
        self,
        test_id: Optional[str] = None,
        test_name: Optional[str] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a synthetic test by ID or name, returning its id, label, and description.

        If test_name is provided instead of test_id, fetches all tests and resolves
        the name to an ID before retrieving the full test record.

        Args:
            test_id: The synthetic test ID (e.g. "CVkDqtbdHMR4pqms7K5N")
            test_name: The synthetic test label (used for name resolution if test_id not given)
            ctx: The MCP context (optional)

        Returns:
            Dictionary with id, label, description, or error information
        """
        try:
            if not test_id and not test_name:
                logger.warning("[get_synthetic_test] Missing required params: either test_id or test_name must be provided")
                return {"error": "Either test_id or test_name is required"}

            # Name resolution: fetch all tests and find the matching label
            if test_name and not test_id:
                logger.debug("[get_synthetic_test] Resolving test name '%s' to test ID", test_name)

                list_response = await sdk_call_with_keepalive(
                    call_sdk_fn(api_client.get_synthetic_tests_without_preload_content),
                    ctx=ctx,
                    operation_name="get_synthetic_tests_for_name_resolution",
                    resource_type=resource_type,
                    tool_name=tool_name,
                )

                if list_response.status != 200:
                    error_body = decode_response(list_response)
                    return {
                        "error": f"Failed to list synthetic tests for name resolution: HTTP {list_response.status}",
                        "details": error_body,
                    }

                tests: List[Dict] = json.loads(decode_response(list_response))

                matched_id = None
                for test in tests:
                    label = test.get("label", "")
                    if label.lower() == test_name.lower():
                        matched_id = test.get("id")
                        break

                if not matched_id:
                    available = [t.get("label") for t in tests if t.get("label")]
                    return {
                        "error": f"No synthetic test found with name '{test_name}'",
                        "available_test_names": available,
                    }

                logger.debug("[get_synthetic_test] Resolved '%s' to ID '%s'", test_name, matched_id)
                test_id = matched_id

            # Fetch the single test by ID
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_synthetic_test_without_preload_content, id=test_id),
                ctx=ctx,
                operation_name="get_synthetic_test",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status != 200:
                error_body = decode_response(response)
                return {
                    "error": f"Failed to get synthetic test: HTTP {response.status}",
                    "details": error_body,
                    "test_id": test_id,
                }

            return json.loads(decode_response(response))

        except Exception as e:
            logger.error("[get_synthetic_test] Error: %s", e, exc_info=True)
            return {"error": f"Failed to get synthetic test: {e!s}"}

    @with_header_auth(SyntheticSettingsApi)
    async def get_synthetic_tests(
        self,
        application_id: Optional[str] = None,
        location_id: Optional[str] = None,
        credential_name: Optional[str] = None,
        sort: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter_param: Optional[str] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List synthetic tests, optionally filtered and paginated.

        All parameters are optional — omitting all returns every test.

        Args:
            application_id: Filter by application ID
            location_id: Filter by location ID
            credential_name: Filter by credential name
            sort: Sort attribute, prefix with '+' (ASC) or '-' (DESC), e.g. "+label"
            offset: Number of pages to skip (used with limit)
            limit: Maximum number of tests to return per page
            filter_param: Attribute filter string e.g. {label=MyTest} with pattern as {<attribute name><operator><attribute value>}
            ctx: The MCP context (optional)

        Returns:
            Dictionary with items (full test records) and count
        """
        try:
            # Normalize filter: API requires {attribute=value} syntax
            if filter_param is not None and not filter_param.startswith("{"):
                filter_param = f"{{{filter_param}}}"

            logger.debug(
                "[get_synthetic_tests] Called with application_id=%s, location_id=%s, "
                "credential_name=%s, sort=%s, offset=%s, limit=%s, filter=%s",
                application_id, location_id, credential_name, sort, offset, limit, filter_param,
            )

            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_synthetic_tests_without_preload_content,
                    application_id=application_id,
                    location_id=location_id,
                    credential_name=credential_name,
                    sort=sort,
                    offset=offset,
                    limit=limit,
                    filter=filter_param,
                ),
                ctx=ctx,
                operation_name="get_synthetic_tests",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status != 200:
                return self.handle_api_error_response(response, "list synthetic tests", logger)

            items = json.loads(decode_response(response))

            logger.debug("[get_synthetic_tests] Returning %d tests", len(items))
            return {
                "items": items,
                "count": len(items),
            }

        except Exception as e:
            logger.error("[get_synthetic_tests] Error: %s", e, exc_info=True)
            return {"error": f"Failed to list synthetic tests: {e!s}"}

    @with_header_auth(SyntheticSettingsApi)
    async def get_locations(
        self,
        location_type: Optional[str] = None,
        status: Optional[str] = None,
        sort: Optional[str] = None,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        filter: Optional[str] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List all synthetic monitoring locations.

        Returns full location records including locationType, geoPoint, playbackCapabilities,
        customProperties, and status. Use locationType="Managed" to retrieve only
        datacenter-backed locations (IBM Cloud / AWS / Azure hosted PoPs).

        Args:
            location_type: Optional filter — "Managed" returns datacenter locations only,
                "Private" returns self-hosted PoPs only. When omitted, all locations are returned.
            status: Optional filter — "Online" returns only currently active locations.
                When omitted, all locations regardless of status are returned.
            sort: Sort attribute, prefix '+' (ASC) or '-' (DESC), e.g. "+label"
            offset: Number of pages to skip (used with limit)
            limit: Maximum number of locations to return per page
            filter: Attribute filter string (see Instana API docs for supported attributes)
            ctx: The MCP context (optional)

        Returns:
            Dictionary with items (full location records), count, and applied filters.
        """
        try:
            logger.debug(
                "[get_locations] Called with location_type=%s, status=%s, "
                "sort=%s, offset=%s, limit=%s, filter=%s",
                location_type, status, sort, offset, limit, filter,
            )

            # When a post-fetch filter (location_type or status) is active, fetch all
            # locations without pagination so that filtering does not silently truncate
            # the result set. Server-side limit/offset are only forwarded when no
            # client-side filter is applied.
            needs_full_fetch = bool(location_type or status)
            response = await sdk_call_with_keepalive(
                call_sdk_fn(
                    api_client.get_synthetic_locations_without_preload_content,
                    sort=sort,
                    offset=None if needs_full_fetch else offset,
                    limit=None if needs_full_fetch else limit,
                    filter=filter,
                ),
                ctx=ctx,
                operation_name="get_synthetic_locations",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status != 200:
                return self.handle_api_error_response(response, "list synthetic locations", logger)

            items: List[Dict] = json.loads(decode_response(response))

            # Apply optional post-fetch filters
            if location_type:
                items = [loc for loc in items if loc.get("locationType", "").lower() == location_type.lower()]
            if status:
                items = [loc for loc in items if loc.get("status", "").lower() == status.lower()]

            logger.debug("[get_locations] Returning %d locations", len(items))
            return {
                "items": items,
                "count": len(items),
                "filters_applied": {
                    "location_type": location_type,
                    "status": status,
                },
            }

        except Exception as e:
            logger.error("[get_locations] Error: %s", e, exc_info=True)
            return {"error": f"Failed to list synthetic locations: {e!s}"}

    @with_header_auth(SyntheticSettingsApi)
    async def get_location_by_id(
        self,
        location_id: Optional[str] = None,
        location_name: Optional[str] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a single synthetic monitoring location by its ID or name.

        If location_name is provided instead of location_id, fetches all locations
        and resolves the name to an ID before retrieving the full record.
        Name matching is case-insensitive and checks both:
          - label       (stable internal name, e.g. "instana-release-aws-ap-south-1-Mumbai")
                        — equivalent to datacenter.locationLabel
          - displayLabel (short human name, e.g. "ap-south-1(Mumbai)")
                        — equivalent to datacenter.label

        Args:
            location_id: The location ID (e.g. "BeeOPKtHGtIOBvaPEMpH")
            location_name: The location label or displayLabel. On no match, the error
                response includes available_location_names with id, label, and displayLabel
                for every known location.
            ctx: The MCP context (optional)

        Returns:
            Dictionary with the full location record, or error information.
        """
        try:
            if not location_id and not location_name:
                logger.warning("[get_location_by_id] Missing required params: either location_id or location_name must be provided")
                return {"error": "Either location_id or location_name is required"}

            # Name resolution: fetch all locations and match on label or displayLabel
            if location_name and not location_id:
                logger.debug("[get_location_by_id] Resolving location name '%s' to ID", location_name)

                list_response = await sdk_call_with_keepalive(
                    call_sdk_fn(api_client.get_synthetic_locations_without_preload_content),
                    ctx=ctx,
                    operation_name="get_synthetic_locations_for_name_resolution",
                    resource_type=resource_type,
                    tool_name=tool_name,
                )

                if list_response.status != 200:
                    return self.handle_api_error_response(list_response, "list synthetic locations for name resolution", logger)

                locations: List[Dict] = json.loads(decode_response(list_response))

                matched_id = None
                name_lower = location_name.lower()
                for loc in locations:
                    if (
                        loc.get("label", "").lower() == name_lower
                        or loc.get("displayLabel", "").lower() == name_lower
                    ):
                        matched_id = loc.get("id")
                        break

                if not matched_id:
                    available = [
                        {"id": loc.get("id"), "label": loc.get("label"), "displayLabel": loc.get("displayLabel")}
                        for loc in locations
                        if loc.get("label")
                    ]
                    return {
                        "error": f"No synthetic location found with name '{location_name}'",
                        "available_location_names": available,
                    }

                logger.debug("[get_location_by_id] Resolved '%s' to ID '%s'", location_name, matched_id)
                location_id = matched_id

            # Fetch the single location by ID
            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_synthetic_location_without_preload_content, id=location_id),
                ctx=ctx,
                operation_name="get_synthetic_location",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status != 200:
                error_body = decode_response(response)
                return {
                    "error": f"Failed to get synthetic location: HTTP {response.status}",
                    "details": error_body,
                    "location_id": location_id,
                }

            logger.debug("[get_location_by_id] Returning location for id=%s", location_id)
            return json.loads(decode_response(response))

        except Exception as e:
            logger.error("[get_location_by_id] Error: %s", e, exc_info=True)
            return {"error": f"Failed to get synthetic location: {e!s}"}

    @with_header_auth(SyntheticSettingsApi)
    async def get_all_datacenters(
        self,
        status: Optional[str] = None,
        ctx=None,
        api_client=None,
        resource_type: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all datacenter-backed synthetic monitoring locations (locationType="Managed").

        Datacenters are Managed PoPs hosted by IBM Cloud, AWS, or Azure. Each record includes:
        - id: The locationId used in all TAG_FILTER expressions
        - label: The stable location label (matches locationLabel in datacenter config APIs)
        - displayLabel: Human-readable name (e.g. "ap-south-1(Mumbai)")
        - geoPoint: {cityName, countryName, latitude, longitude}
        - customProperties.datacenterFlag: Stable datacenter identifier code
        - status: "Online" or "Offline"
        - totalTests: Number of synthetic tests linked to this datacenter

        Use this to resolve datacenter names/codes to locationIds before filtering
        test playback data. Join on label to match locationStatusList entries from
        get_test_summary_list.

        Args:
            status: Optional — "Online" to return only currently active datacenters.
                When omitted, all Managed locations are returned regardless of status.
            ctx: The MCP context (optional)

        Returns:
            Dictionary with items (Managed location records), count, and total_online count.
        """
        try:
            logger.debug("[get_all_datacenters] Called with status=%s", status)

            response = await sdk_call_with_keepalive(
                call_sdk_fn(api_client.get_synthetic_locations_without_preload_content),
                ctx=ctx,
                operation_name="get_synthetic_locations_datacenters",
                resource_type=resource_type,
                tool_name=tool_name,
            )

            if response.status != 200:
                return self.handle_api_error_response(response, "list synthetic locations", logger)

            all_locations: List[Dict] = json.loads(decode_response(response))

            # Datacenters are exclusively Managed locations
            datacenters = [loc for loc in all_locations if loc.get("locationType", "").lower() == "managed"]

            # Compute total_online from the full Managed list BEFORE applying the optional
            # status filter, so it always represents the true fleet size regardless of
            # which subset the caller requested.
            online_count = sum(1 for dc in datacenters if dc.get("status", "").lower() == "online")

            if status:
                datacenters = [dc for dc in datacenters if dc.get("status", "").lower() == status.lower()]

            logger.debug("[get_all_datacenters] Returning %d datacenter locations", len(datacenters))
            return {
                "items": datacenters,
                "count": len(datacenters),
                "total_online": online_count,
                "filters_applied": {
                    "location_type": "Managed",
                    "status": status,
                },
            }

        except Exception as e:
            logger.error("[get_all_datacenters] Error: %s", e, exc_info=True)
            return {"error": f"Failed to get datacenter locations: {e!s}"}
