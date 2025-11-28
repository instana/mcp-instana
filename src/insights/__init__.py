"""
Insights module for Instana MCP tools.
"""

# from src.insights.entities_insight import ApplicationEntitiesInsightMCPTools
from src.insights.application_metrics_insight import ApplicationMetricsInsightMCPTools
from src.insights.infrastructure_metrics_insight import InfrastructureMetricsInsightMCPTools

__all__ = [
    # "ApplicationEntitiesInsightMCPTools",
    "ApplicationMetricsInsightMCPTools",
    "InfrastructureMetricsInsightMCPTools"
]

# Made with Bob
