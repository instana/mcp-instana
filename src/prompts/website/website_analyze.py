from typing import Optional

from src.prompts import auto_register_prompt


class WebsiteAnalyzePrompts:
    """Class containing website analyze related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_website_beacon_groups(payload: Optional[dict] = None, fill_time_series: Optional[bool] = None) -> str:
        """Retrieve grouped website beacon metrics for analyzing performance across different dimensions like page URLs, browsers, or geographic locations"""
        return f"""
        Get website beacon groups with payload:
        - Payload: {payload or 'None (will use default payload)'}
        - Fill time series: {fill_time_series or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_website_beacons(payload: Optional[dict] = None, fill_time_series: Optional[bool] = None) -> str:
        """Retrieve individual website beacon metrics providing detailed information about specific beacon events"""
        return f"""
        Get website beacons with payload:
        - Payload: {payload or 'None (will use default payload)'}
        - Fill time series: {fill_time_series or 'None'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_website_beacon_groups', cls.get_website_beacon_groups),
            ('get_website_beacons', cls.get_website_beacons),
        ]
