from typing import List, Optional

from src.prompts import auto_register_prompt


class MobileAppAlertPrompts:
    """Prompts for mobile app alert configuration tools"""

    @auto_register_prompt
    @staticmethod
    def find_active_mobile_app_alert_configs(
        mobile_app_id: str,
        alert_ids: Optional[List[str]] = None
    ) -> str:
        """
        Retrieve all alert configurations for a specific mobile app.

        Use this to fetch all alert configurations associated with a mobile app,
        optionally filtered by specific alert IDs.
        """
        return f"""
        Retrieve all mobile app alert configurations for mobile app ID: {mobile_app_id}.
        Parameters:
        - mobile_app_id: {mobile_app_id}
        - alert_ids: {alert_ids if alert_ids is not None else 'None (fetch all)'}
        """

    @auto_register_prompt
    @staticmethod
    def find_mobile_app_alert_config(
        id: str,
        valid_on: Optional[int] = None
    ) -> str:
        """
        Retrieve a specific mobile app alert configuration by ID.

        Use this to fetch a single configuration by its alert config ID,
        optionally at a specific point in time.
        """
        return f"""
        Retrieve mobile app alert configuration by ID.
        Parameters:
        - id: {id}
        - valid_on: {valid_on if valid_on is not None else 'None (latest version)'}
        """

    @classmethod
    def get_prompts(cls):
        return [
            ('find_active_mobile_app_alert_configs', cls.find_active_mobile_app_alert_configs),
            ('find_mobile_app_alert_config', cls.find_mobile_app_alert_config),
        ]
