from typing import Optional

from src.prompts import auto_register_prompt


class MobileAppAnalyzePrompts:
    """Class containing mobile app analyze related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_mobile_app_beacon_groups(payload: Optional[dict] = None, fill_time_series: Optional[bool] = None) -> str:
        """Retrieve grouped mobile app beacon metrics for analyzing performance across different dimensions like mobile apps, browsers, or geographic locations

        CRITICAL: Entity field is REQUIRED for ALL tag filters
        - ALWAYS set "entity": "NOT_APPLICABLE" for ALL mobile app beacon tags
        - This applies to ALL tags: mobileBeacon.mobileApp.*, mobileBeacon.view.*, mobileBeacon.device.*, mobileBeacon.geo.*, etc.
        - The entity field is MANDATORY - never omit it
        - Examples:
          * {"type": "TAG_FILTER", "name": "mobileBeacon.mobileApp.name", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Robot Shop"}
          * {"type": "TAG_FILTER", "name": "mobileBeacon.view.name", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Products"}
          * {"type": "TAG_FILTER", "name": "mobileBeacon.device.model", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Google Pixel 4XL"}
        """
        return f"""
        Get mobile app beacon groups with payload:
        - Payload: {payload if payload is not None else 'None (will use default payload)'}
        - Fill time series: {fill_time_series if fill_time_series is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_all_mobile_app_beacons(payload: Optional[dict] = None, fill_time_series: Optional[bool] = None) -> str:
        """Retrieve individual mobile app beacon metrics providing detailed information about specific beacon events

        CRITICAL: Entity field is REQUIRED for ALL tag filters
        - ALWAYS set "entity": "NOT_APPLICABLE" for ALL mobile app beacon tags
        - This applies to ALL tags: mobileBeacon.mobileApp.*, mobileBeacon.view.*, mobileBeacon.device.*, mobileBeacon.geo.*, etc.
        - The entity field is MANDATORY - never omit it
        - Examples:
          * {"type": "TAG_FILTER", "name": "mobileBeacon.mobileApp.name", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Robot Shop"}
          * {"type": "TAG_FILTER", "name": "mobileBeacon.view.name", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Products"}
          * {"type": "TAG_FILTER", "name": "mobileBeacon.device.model", "operator": "EQUALS", "entity": "NOT_APPLICABLE", "value": "Google Pixel 4XL"}
        """
        return f"""
        Get all mobile app beacons with payload:
        - Payload: {payload if payload is not None else 'None (will use default payload)'}
        - Fill time series: {fill_time_series if fill_time_series is not None else 'None'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_mobile_app_beacon_groups', cls.get_mobile_app_beacon_groups),
            ('get_all_mobile_app_beacons', cls.get_all_mobile_app_beacons),
        ]
