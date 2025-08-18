from typing import Optional

from src.prompts import auto_register_prompt


class ApplicationMetricsPrompts:
    """Class containing application metrics related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_application_metrics(application_ids: Optional[list] = None, metrics: Optional[list] = None, time_frame: Optional[dict] = None, fill_time_series: Optional[bool] = None) -> str:
        """Retrieve metrics for specific applications including latency, error rates, etc., over a given time frame"""
        return f"""
        Get application metrics for:
        - Application IDs: {application_ids or 'None'}
        - Metrics: {metrics or 'None'}
        - Time frame: {time_frame or 'None'}
        - Fill time series: {fill_time_series or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_application_endpoints_metrics(application_ids: Optional[list] = None, metrics: Optional[list] = None, time_frame: Optional[dict] = None, order: Optional[dict] = None, pagination: Optional[dict] = None, filters: Optional[dict] = None, fill_time_series: Optional[bool] = None) -> str:
        """Retrieve metrics for endpoints within an application, such as latency, error rates, and call counts"""
        return f"""
        Get endpoint metrics for applications:
        - Application IDs: {application_ids}
        - Metrics: {metrics}
        - Time frame: {time_frame}
        - Order: {order or 'None'}
        - Pagination: {pagination or 'None'}
        - Filters: {filters or 'None'}
        - Fill time series: {fill_time_series or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_application_service_metrics(service_ids: list, metrics: Optional[list] = None, var_from: Optional[int] = None, to: Optional[int] = None, fill_time_series: Optional[bool] = None, include_snapshot_ids: Optional[bool] = None) -> str:
        """Fetch metrics over a specific time frame for specific services"""
        return f"""
        Get service metrics:
        - Service IDs: {service_ids}
        - Metrics: {metrics or 'None'}
        - From: {var_from or '1 hour ago'}
        - To: {to or 'now'}
        - Fill time series: {fill_time_series or 'None'}
        - Include snapshot IDs: {include_snapshot_ids or 'None'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_application_metrics', cls.get_application_metrics),
            ('get_application_endpoints_metrics', cls.get_application_endpoints_metrics),
            ('get_application_service_metrics', cls.get_application_service_metrics),
        ]
