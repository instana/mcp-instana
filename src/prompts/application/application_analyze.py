from typing import Optional

from src.prompts import auto_register_prompt


class ApplicationAnalyzePrompts:
    """Class containing application analyze related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_all_traces(payload: Optional[dict] = None) -> str:
        """Retrieve traces for application analysis.

        The payload can include timeFrame, tagFilterExpression, pagination, and order.
        """
        return f"""
        Get all application traces with:
        - Payload: {payload if payload is not None else 'None (will use default payload)'}
        """

    @auto_register_prompt
    @staticmethod
    def get_trace_details(trace_id: str, retrieval_size: Optional[int] = None, offset: Optional[int] = None, ingestion_time: Optional[int] = None) -> str:
        """Retrieve detailed call-level data for a single trace."""
        return f"""
        Get trace details with:
        - Trace ID: {trace_id}
        - Retrieval size: {retrieval_size if retrieval_size is not None else 'None'}
        - Offset: {offset if offset is not None else 'None'}
        - Ingestion time: {ingestion_time if ingestion_time is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_trace_groups(payload: Optional[dict] = None) -> str:
        """Retrieve grouped trace metrics from the application analyze API.

        CRITICAL:
        - payload.group and payload.metrics are required for group queries.
        - Use trace metrics (for example: "traces"), not call metrics.
        """
        return f"""
        Get grouped application traces with:
        - Payload: {payload if payload is not None else 'None'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ("get_all_traces", cls.get_all_traces),
            ("get_trace_details", cls.get_trace_details),
            ("get_trace_groups", cls.get_trace_groups),
        ]
