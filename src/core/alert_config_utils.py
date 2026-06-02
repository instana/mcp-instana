"""
Shared utilities for alert configuration operations.

This module provides common functionality for mobile app and website alert configurations
to reduce code duplication.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_alert_config_response(response, resource_type: str, resource_id: str) -> Dict[str, Any]:
    """
    Parse alert configuration response from API.

    Args:
        response: Raw API response object
        resource_type: Type of resource (e.g., "mobile app", "website")
        resource_id: ID of the resource

    Returns:
        Dictionary containing parsed configurations or error information
    """
    try:
        raw_data = response.data.decode('utf-8')
        logger.debug(f"Raw data: {raw_data}")

        result = json.loads(raw_data)
        logger.debug(f"Parsed JSON result: {result}")

        if isinstance(result, list):
            configs = result
        else:
            configs = [result] if result else []

        # Limit to first 10 results
        total_count = len(configs)
        limited_configs = configs[:10]

        # Provide helpful feedback based on the result
        if not configs:
            return {
                "configs": [],
                "count": 0,
                "total": 0,
                "showing": 0,
                "message": f"No active alert configurations found for {resource_type} ID: {resource_id}",
                "suggestion": "You can create a new alert configuration if needed."
            }
        else:
            return {
                "configs": limited_configs,
                "count": len(limited_configs),
                "total": total_count,
                "showing": len(limited_configs),
                "message": f"Found {total_count} active alert configuration(s) for {resource_type} ID: {resource_id}. Showing first {len(limited_configs)}."
            }

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse response JSON: {e}"
        logger.error(error_msg)
        return {"error": error_msg}


def parse_single_alert_config_response(response) -> Dict[str, Any]:
    """
    Parse single alert configuration response from API.

    Args:
        response: Raw API response object

    Returns:
        Dictionary containing parsed configuration or error information
    """
    try:
        raw_data = response.data.decode('utf-8')
        logger.debug(f"Raw data: {raw_data}")

        result_dict = json.loads(raw_data)
        logger.debug(f"Parsed JSON result: {result_dict}")
        return result_dict

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse response JSON: {e}"
        logger.error(error_msg)
        return {"error": error_msg}
