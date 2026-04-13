"""
SLO Report MCP Tools Module

This module provides SLO (Service Level Objective) report tools for Instana.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import Context

# Import the necessary classes from the Instana SDK
try:
    from instana_client.api.service_levels_objective_slo_report_api import (
        ServiceLevelsObjectiveSLOReportApi,
    )
except ImportError:
    logging.getLogger(__name__).error("Instana SDK not available. Please install the Instana SDK.", exc_info=True)
    raise

from src.core.utils import BaseInstanaClient, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class SLOReportMCPTools(BaseInstanaClient):
    """Tools for SLO reports in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the SLO Report MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    def _clean_slo_report_data(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean SLO report data for LLM consumption.

        Keeps key metrics and simplifies chart data:
        - Current SLI/SLO values
        - Error budget metrics
        - Burn rate
        - Time range
        - Simplified chart data (only if present)

        Args:
            report: Raw SLO report dictionary from API

        Returns:
            Cleaned SLO report dictionary optimized for LLM consumption
        """
        cleaned = {
            "sli": report.get("sli"),
            "slo": report.get("slo"),
            "fromTimestamp": report.get("fromTimestamp"),
            "toTimestamp": report.get("toTimestamp"),
            "errorBudgetRemaining": report.get("errorBudgetRemaining"),
            "errorBudgetSpent": report.get("errorBudgetSpent"),
            "totalErrorBudget": report.get("totalErrorBudget"),
            "errorBurnRate": report.get("errorBurnRate"),
        }

        # Include chart data if present (but keep it optional for cleaner output)
        if report.get("errorChart"):
            cleaned["errorChart"] = report.get("errorChart")
        if report.get("errorBudgetRemainChart"):
            cleaned["errorBudgetRemainChart"] = report.get("errorBudgetRemainChart")
        if report.get("errorBurnRateChart"):
            cleaned["errorBurnRateChart"] = report.get("errorBurnRateChart")
        if report.get("violationDistribution"):
            cleaned["violationDistribution"] = report.get("violationDistribution")
        if report.get("errorAccumulationChart"):
            cleaned["errorAccumulationChart"] = report.get("errorAccumulationChart")

        return cleaned

    @with_header_auth(ServiceLevelsObjectiveSLOReportApi)
    async def get_slo_report(self,
        slo_id: str,
        var_from: Optional[str] = None,
        to: Optional[str] = None,
        exclude_correction_id: Optional[List[str]] = None,
        include_correction_id: Optional[List[str]] = None,
        ctx: Optional[Context] = None,
        api_client: Any = None
    ) -> Dict[str, Any]:
        """
        Generate Service Levels report for a specific SLO configuration.

        Args:
            slo_id: SLO configuration ID (required)
            var_from: Starting point for data retrieval (13 digit Unix timestamp in milliseconds)
            to: Ending point for data retrieval (13 digit Unix timestamp in milliseconds)
            exclude_correction_id: IDs of correction configurations to exclude
            include_correction_id: IDs of correction configurations to include
            ctx: Optional context
            api_client: Optional API client

        Returns:
            Dict containing the SLO report data with metrics and charts
        """
        try:
            if not slo_id:
                return {"error": "slo_id is required"}

            logger.debug(f"get_slo_report called with slo_id: {slo_id}")

            # Call the API method
            result = api_client.get_slo_without_preload_content(
                slo_id=slo_id,
                var_from=var_from,
                to=to,
                exclude_correction_id=exclude_correction_id,
                include_correction_id=include_correction_id
            )

            # Check HTTP status code
            logger.debug(f"API response status: {result.status}")

            # Handle non-success status codes
            if result.status >= 400:
                error_text = result.data.decode('utf-8') if result.data else "No error details provided"
                logger.error(f"API returned error status {result.status}: {error_text}")
                return {
                    "error": f"API error (status {result.status}): {error_text}",
                    "status_code": result.status
                }

            # Parse the JSON response manually
            try:
                response_text = result.data.decode('utf-8')
                logger.debug(f"Response text length: {len(response_text)}")

                if not response_text or response_text.strip() == "":
                    logger.warning("Empty response from API")
                    return {
                        "error": "Empty response from API",
                        "status_code": result.status
                    }

                result_list = json.loads(response_text)
                logger.debug(f"Parsed JSON response type: {type(result_list)}, length: {len(result_list) if isinstance(result_list, list) else 'N/A'}")
                logger.debug(f"First 200 chars of response: {response_text[:200]}")
            except (json.JSONDecodeError, AttributeError) as json_err:
                error_message = f"Failed to parse JSON response: {json_err}"
                logger.error(f"{error_message}. Response text: {response_text if 'response_text' in locals() else 'N/A'}")
                return {
                    "error": error_message,
                    "raw_response": response_text if 'response_text' in locals() else None,
                    "status_code": result.status
                }

            # The API returns a list of reports
            if isinstance(result_list, list):
                logger.debug(f"result_list is a list with {len(result_list)} items")
                if len(result_list) > 0:
                    # Clean each report in the list
                    cleaned_reports = [self._clean_slo_report_data(report) for report in result_list]
                    logger.debug(f"Cleaned {len(cleaned_reports)} SLO reports")
                    return {
                        "success": True,
                        "reports": cleaned_reports,
                        "count": len(cleaned_reports),
                        "status_code": result.status
                    }
                else:
                    logger.warning("result_list is empty")
                    return {
                        "success": True,
                        "reports": [],
                        "count": 0,
                        "message": "No reports found for the specified SLO and time range",
                        "status_code": result.status
                    }
            else:
                logger.warning(f"result_list is not a list, it's a {type(result_list)}: {result_list}")
                return {
                    "success": True,
                    "reports": [],
                    "count": 0,
                    "message": f"Unexpected response format: {type(result_list)}",
                    "status_code": result.status,
                    "raw_data": result_list
                }

        except Exception as e:
            logger.error(f"Error in get_slo_report: {e}", exc_info=True)
            return {"error": f"Failed to get SLO report: {e!s}"}
