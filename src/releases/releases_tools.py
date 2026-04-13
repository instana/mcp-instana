"""
Releases MCP Tools

This module provides MCP tools for managing Instana releases.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import Context
from instana_client.api.releases_api import ReleasesApi
from instana_client.models.release import Release

from src.core.utils import BaseInstanaClient, with_header_auth

logger = logging.getLogger(__name__)


class ReleasesMCPTools(BaseInstanaClient):
    """
    MCP Tools for Instana Releases API.

    Provides operations for managing releases including:
    - Getting all releases
    - Getting a specific release by ID
    - Creating a new release
    - Updating an existing release
    - Deleting a release
    """

    def __init__(self, read_token: str, base_url: str):
        """
        Initialize the Releases MCP Tools.

        Args:
            read_token: Instana API token
            base_url: Instana API base URL
        """
        super().__init__(read_token=read_token, base_url=base_url)
        logger.info("Releases MCP Tools initialized")

    @with_header_auth(ReleasesApi)
    async def get_all_releases(
        self,
        from_time: Optional[int] = None,
        to_time: Optional[int] = None,
        name_filter: Optional[str] = None,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """
        Get all releases within a time range with pagination and filtering support.

        Args:
            from_time: Start timestamp in milliseconds (optional)
            to_time: End timestamp in milliseconds (optional)
            name_filter: Filter releases by name (case-insensitive substring match, optional)
            page_number: Page number for pagination (1-based, optional)
            page_size: Number of results per page (optional, default: 50)
            ctx: MCP context (internal)

        Returns:
            Dictionary containing:
                - success: Boolean indicating success
                - count: Total number of releases matching filters
                - page_number: Current page number (if pagination used)
                - page_size: Size of each page (if pagination used)
                - total_pages: Total number of pages (if pagination used)
                - releases: List of releases for current page
                - has_next_page: Boolean indicating if more pages exist
                - has_previous_page: Boolean indicating if previous pages exist
        """
        try:
            logger.info(
                f"Getting all releases: from={from_time}, to={to_time}, "
                f"name_filter={name_filter}, page_number={page_number}, page_size={page_size}"
            )

            # Use without_preload_content to avoid pydantic validation issues
            # Note: The API doesn't support pagination natively, so we fetch all and paginate locally
            # Map our parameter names to API parameter names (var_from, to)
            response = api_client.get_all_releases_without_preload_content(
                var_from=from_time,
                to=to_time
            )

            # Read and parse the response
            response_data = response.read()
            all_releases = json.loads(response_data) if response_data else []

            # Apply name filtering if specified
            if name_filter:
                name_filter_lower = name_filter.lower()
                all_releases = [
                    release for release in all_releases
                    if name_filter_lower in release.get("name", "").lower()
                ]
                logger.info(f"Filtered to {len(all_releases)} releases matching name '{name_filter}'")

            total_count = len(all_releases)

            # Apply pagination if specified
            if page_number is not None and page_size is not None:
                # Validate pagination parameters
                if page_number < 1:
                    return {
                        "success": False,
                        "error": "page_number must be >= 1"
                    }
                if page_size < 1:
                    return {
                        "success": False,
                        "error": "page_size must be >= 1"
                    }

                # Calculate pagination
                start_idx = (page_number - 1) * page_size
                end_idx = start_idx + page_size
                total_pages = (total_count + page_size - 1) // page_size  # Ceiling division

                # Get the page slice
                paginated_releases = all_releases[start_idx:end_idx]

                logger.info(
                    f"Retrieved page {page_number}/{total_pages} "
                    f"({len(paginated_releases)} releases)"
                )

                return {
                    "success": True,
                    "count": total_count,
                    "page_number": page_number,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "releases": paginated_releases,
                    "has_next_page": page_number < total_pages,
                    "has_previous_page": page_number > 1
                }
            else:
                # No pagination - return all results
                # Set default page_size for consistency
                default_page_size = page_size or 50

                logger.info(f"Retrieved {total_count} releases (no pagination)")

                return {
                    "success": True,
                    "count": total_count,
                    "releases": all_releases,
                    "pagination_hint": (
                        f"Consider using pagination for large result sets. "
                        f"Use page_number=1 and page_size={default_page_size} to get started."
                    ) if total_count > default_page_size else None
                }

        except Exception as e:
            logger.error(f"Error getting all releases: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to get releases: {e!s}"
            }

    @with_header_auth(ReleasesApi)
    async def get_release(
        self,
        release_id: str,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """
        Get a specific release by ID.

        Args:
            release_id: The unique ID of the release
            ctx: MCP context (internal)

        Returns:
            Dictionary containing the release details
        """
        try:
            logger.info(f"Getting release with ID: {release_id}")

            # Use without_preload_content to avoid pydantic validation issues
            response = api_client.get_release_without_preload_content(
                release_id=release_id
            )

            # Read and parse the response
            response_data = response.read()
            release_dict = json.loads(response_data) if response_data else None

            logger.info(f"Retrieved release: {release_id}")

            return {
                "success": True,
                "release": release_dict
            }

        except Exception as e:
            logger.error(f"Error getting release {release_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to get release: {e!s}",
                "release_id": release_id
            }

    @with_header_auth(ReleasesApi)
    async def create_release(
        self,
        name: str,
        start: int,
        applications: Optional[List[Dict[str, str]]] = None,
        services: Optional[List[Dict[str, Any]]] = None,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """
        Create a new release.

        Args:
            name: Name of the release (e.g., "frontend/release-2000")
            start: Start timestamp in milliseconds
            applications: List of application scopes (optional)
                Each item should have: {"name": "app_name"}
            services: List of service scopes (optional)
                Each item should have: {"name": "service_name", "scopedTo": {...}}
            ctx: MCP context (internal)

        Returns:
            Dictionary containing the created release details
        """
        try:
            logger.info(f"Creating release: {name}")

            # Build the release payload
            release_data = {
                "name": name,
                "start": start
            }

            if applications:
                release_data["applications"] = applications

            if services:
                release_data["services"] = services

            # Create Release object
            release = Release.from_dict(release_data)

            if not release:
                raise ValueError("Failed to create Release object from data")

            # Use without_preload_content to avoid pydantic validation issues
            response = api_client.post_release_without_preload_content(
                release=release
            )

            # Read and parse the response
            response_data = response.read()
            release_dict = json.loads(response_data) if response_data else None

            logger.info(f"Created release: {name}")

            return {
                "success": True,
                "release": release_dict
            }

        except Exception as e:
            logger.error(f"Error creating release {name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to create release: {e!s}",
                "name": name
            }

    @with_header_auth(ReleasesApi)
    async def update_release(
        self,
        release_id: str,
        name: str,
        start: int,
        applications: Optional[List[Dict[str, str]]] = None,
        services: Optional[List[Dict[str, Any]]] = None,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """
        Update an existing release.

        Args:
            release_id: The unique ID of the release to update
            name: Name of the release
            start: Start timestamp in milliseconds
            applications: List of application scopes (optional)
            services: List of service scopes (optional)
            ctx: MCP context (internal)

        Returns:
            Dictionary containing the updated release details
        """
        try:
            logger.info(f"Updating release: {release_id}")

            # Build the release payload
            release_data = {
                "name": name,
                "start": start
            }

            if applications:
                release_data["applications"] = applications

            if services:
                release_data["services"] = services

            # Create Release object
            release = Release.from_dict(release_data)

            if not release:
                raise ValueError("Failed to create Release object from data")

            # Use without_preload_content to avoid pydantic validation issues
            response = api_client.put_release_without_preload_content(
                release_id=release_id,
                release=release
            )

            # Read and parse the response
            response_data = response.read()
            release_dict = json.loads(response_data) if response_data else None

            logger.info(f"Updated release: {release_id}")

            return {
                "success": True,
                "release": release_dict
            }

        except Exception as e:
            logger.error(f"Error updating release {release_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to update release: {e!s}",
                "release_id": release_id
            }

    @with_header_auth(ReleasesApi)
    async def delete_release(
        self,
        release_id: str,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """
        Delete a release.

        Args:
            release_id: The unique ID of the release to delete
            ctx: MCP context (internal)

        Returns:
            Dictionary indicating success or failure
        """
        try:
            logger.info(f"Deleting release: {release_id}")

            # Use without_preload_content to avoid pydantic validation issues
            response = api_client.delete_release_without_preload_content(
                release_id=release_id
            )

            # Read the response (delete typically returns empty response)
            response.read()

            logger.info(f"Deleted release: {release_id}")

            return {
                "success": True,
                "message": f"Release {release_id} deleted successfully",
                "release_id": release_id
            }

        except Exception as e:
            logger.error(f"Error deleting release {release_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Failed to delete release: {e!s}",
                "release_id": release_id
            }
