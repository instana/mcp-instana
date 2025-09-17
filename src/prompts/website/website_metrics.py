from typing import Optional

from src.prompts import auto_register_prompt


class WebsiteMetricsPrompts:
    """Class containing website metrics related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_website_beacon_metrics_v2(payload: Optional[dict] = None) -> str:
        """Retrieve website beacon metrics using the v2 API including page load times, error rates, etc., over a given time frame"""
        return f"""
        Get website beacon metrics v2 with payload:
        - Payload: {payload or 'None (will use default payload)'}
        """

    @auto_register_prompt
    @staticmethod
    def get_website_page_load(page_id: str, timestamp: int) -> str:
        """Retrieve detailed beacon information for a specific page load event"""
        return f"""
        Get website page load details:
        - Page ID: {page_id}
        - Timestamp: {timestamp}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_website_beacon_metrics_v2', cls.get_website_beacon_metrics_v2),
            ('get_website_page_load', cls.get_website_page_load),
        ]
