"""
Infrastructure Metrics MCP Prompts Module

This module provides infrastructure metrics-specific MCP prompts for Instana monitoring.
"""

from typing import Callable, List, Optional, Tuple

from src.prompts import auto_register_prompt


class InfrastructureMetricsPrompts:
    """Class containing prompts for infrastructure metrics in Instana."""

    @auto_register_prompt
    @staticmethod
    def get_infrastructure_metrics(
        offline: bool,
        rollup: int,
        plugin: str,
        window_size: Optional[int] = None,
        query: Optional[str] = None,
        metrics: Optional[List] = None,
        snapshot_ids: Optional[List] = None,
        to: Optional[int] = None,
    ) -> str:
        """Retrieve infrastructure metrics for plugin and query with a given time frame"""
        return f"""
        Get infrastructure metrics:
        - Plugin: {plugin}
        - Query: {query}
        - Metrics: {metrics}
        - Snapshot IDs: {snapshot_ids or 'None'}
        - Offline: {offline or 'False'}
        - Window size: {window_size or '1 hour'}
        - To: {to or 'current time'}
        - Rollup: {rollup or '60 seconds'}
        """

    @classmethod
    def get_prompts(cls) -> List[Tuple[str, Callable]]:
        """Get all prompts defined in this class"""
        return [
            ('get_infrastructure_metrics', cls.get_infrastructure_metrics),
        ]
