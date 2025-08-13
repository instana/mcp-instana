"""
Infrastructure Analyze MCP Prompts Module

This module provides infrastructure analyze-specific MCP prompts for Instana monitoring.
"""

from typing import Callable, Dict, List, Optional, Tuple

from src.prompts import auto_register_prompt


class InfrastructureAnalyzePrompts:
    """Class containing prompts for infrastructure analysis in Instana."""

    @auto_register_prompt
    @staticmethod
    def infra_available_metrics(
        type: str,
        query: Optional[str] = None,
        var_from: Optional[int] = None,
        to: Optional[int] = None,
        windowSize: Optional[int] = None) -> str:
        """Get available infrastructure metrics for a given entity type"""
        return f"""
        Get available infrastructure metrics:
        - Type: {type}
        - Query: {query or 'None'}
        - From: {var_from or 'None'}
        - To: {to or 'None'}
        - Window size: {windowSize or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def infra_get_entities(
        type: str,
        metrics: Optional[str] = None,
        windowSize: Optional[int] = None,
        to: Optional[int] = None) -> str:
        """Fetch infrastructure entities and their metrics"""
        return f"""
        Get infrastructure entities:
        - Type: {type}
        - Metrics: {metrics}
        - Window size: {windowSize or 'None'}
        - To: {to or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def infra_available_plugins(
        offline: bool,
        query: Optional[str] = None,
        windowSize: Optional[int] = None,
        to: Optional[int] = None) -> str:
        """List available infrastructure monitoring plugins"""
        return f"""
        Get available infrastructure plugins:
        - Query: {query or 'None'}
        - Offline: {offline or 'False'}
        - Window size: {windowSize or 'None'}
        - To: {to or 'None'}
        """

    @classmethod
    def get_prompts(cls) -> List[Tuple[str, Callable]]:
        """Get all prompts defined in this class"""
        return [
            ('infra_available_metrics', cls.infra_available_metrics),
            ('infra_get_entities', cls.infra_get_entities),
            ('infra_available_plugins', cls.infra_available_plugins),
        ]
