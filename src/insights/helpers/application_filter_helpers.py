"""
Application Filter Helper Functions for Instana Insights

Provides reusable helper class for filtering and fetching applications by service criteria.
Can be used by both application metrics and infrastructure metrics tools.
"""
import logging
from typing import Any, Dict, List

from src.core.utils import BaseInstanaClient, with_header_auth

# Import SDK classes
try:
    from instana_client.api.application_metrics_api import ApplicationMetricsApi
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.error(f"Error importing Instana SDK: {e}", exc_info=True)
    raise

# Configure logger for this module
logger = logging.getLogger(__name__)


class ApplicationFilterHelpers(BaseInstanaClient):
    """Helper class for filtering applications by service criteria and fetching their metrics."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the application filter helpers."""
        super().__init__(read_token=read_token, base_url=base_url)
        # Import here to avoid circular dependency
        from src.insights.helpers.metrics_filter_helpers import MetricsFilterHelpers
        self.metrics_filter_helpers = MetricsFilterHelpers(read_token=read_token, base_url=base_url)

    @with_header_auth(ApplicationMetricsApi)
    async def list_applications_by_service_filters(
        self,
        service_name: str,
        plugin_type: str,
        metrics: List[Dict[str, str]],
        time_frame: Dict[str, int],
        include_metrics: bool,
        fetch_applications_func,
        ctx=None,
        api_client=None
    ) -> Dict[str, Any]:
        """
        List applications that contain services matching service name and plugin type.
        
        This is a reusable helper that can be used by both application metrics and 
        infrastructure metrics tools. It filters applications by service criteria and
        optionally fetches their metrics using the provided fetch function.
        
        Args:
            service_name: Service name pattern to match
            plugin_type: Plugin type to filter by
            metrics: List of metrics to fetch
            time_frame: Time range dictionary
            include_metrics: Whether to include metrics in response
            fetch_applications_func: Async function to fetch application metrics
                                    Should accept (api_client, metrics, time_frame, include_metrics, **kwargs)
            api_client: ApplicationMetricsApi client (injected by decorator)
        
        Returns:
            Dictionary with matching applications and their metrics (if requested)
        """
        try:
            # Use the filter helper to find matching applications
            filter_result = await self.metrics_filter_helpers.find_applications_by_service_criteria(
                service_name_pattern=service_name,
                plugin_type=plugin_type,
                time_frame=time_frame
            )
            
            if "error" in filter_result:
                return filter_result
            
            matching_apps = filter_result.get("matching_applications", [])
            
            if not matching_apps:
                return {
                    "query_type": "list_applications_by_service_filters",
                    "applications": [],
                    "summary": {
                        **filter_result.get("summary", {}),
                        "message": "No applications found matching the specified service criteria"
                    }
                }
            
            # If metrics not requested, return just the application list
            if not include_metrics:
                apps_list = []
                for app in matching_apps:
                    apps_list.append({
                        "id": app.get("application_id"),
                        "name": app.get("application_name"),
                        "matching_services": app.get("matching_services", [])
                    })
                
                return {
                    "query_type": "list_applications_by_service_filters",
                    "applications": apps_list,
                    "summary": {
                        **filter_result.get("summary", {}),
                        "note": "Application names only (no metrics)"
                    }
                }
            
            # Get metrics for each matching application
            apps_with_metrics = []
            
            for app in matching_apps:
                app_name = app.get("application_name")
                
                # Get application metrics using the provided function
                app_metrics_result = await fetch_applications_func(
                    api_client, metrics, time_frame, include_metrics=True,
                    nameFilter=app_name
                )
                
                app_metrics = None
                if "applications_with_metrics" in app_metrics_result:
                    apps_list = app_metrics_result["applications_with_metrics"]
                    if apps_list:
                        app_metrics = apps_list[0]
                
                # Add matching services info to the metrics
                if app_metrics:
                    app_metrics["matching_services"] = app.get("matching_services", [])
                    apps_with_metrics.append(app_metrics)
            
            return {
                "query_type": "list_applications_by_service_filters_with_metrics",
                "applications_with_metrics": apps_with_metrics,
                "summary": {
                    **filter_result.get("summary", {}),
                    "metrics_requested": [f"{m['metric']}:{m['aggregation']}" for m in metrics]
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing applications by service filters: {e}", exc_info=True)
            return {"error": f"Failed to list applications by service filters: {e!s}"}


#  