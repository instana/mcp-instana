from typing import Optional

from src.prompts import auto_register_prompt


class SyntheticMetricsPrompts:
    """Class containing synthetic metrics related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_metrics_result(payload: Optional[dict] = None) -> str:
        """Retrieve aggregated synthetic monitoring metrics for one or more metricIds over a given time frame"""
        return f"""
        Get synthetic monitoring metrics with payload:
        - Payload: {payload or '(not specified)'}

        The payload must include:
        - metrics (required): List of metric/aggregation objects, e.g. [{{"metric": "synthetic.metricsResponseTime", "aggregation": "SUM"}}]
        - timeFrame (optional): {{"to": <unix_ms>, "windowSize": <milliseconds>}}
        - pagination (optional): {{"page": 1, "pageSize": 3}}
        - groups (optional): List of grouping objects, e.g. [{{"groupbyTag": "synthetic.applicationId"}}]
        - tagFilterExpression (optional): Tag filter expression object
        - disableDefaultGroups (optional): boolean
        - includeAggregatedTestIds (optional): boolean

        Use get_synthetic_catalog_metrics first to discover valid metricIds and supported aggregations.
        Use get_synthetic_tag_catalog first to discover valid tag names for grouping and filtering.
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_metrics_result', cls.get_metrics_result),
        ]
