from typing import List, Optional

from src.prompts import auto_register_prompt


class WebsiteAlertPrompts:
    """Prompts for website alert configuration tools"""

    @auto_register_prompt
    @staticmethod
    def find_active_website_alert_configs(
        website_id: str,
        alert_ids: Optional[List[str]] = None
    ) -> str:
        """
        Retrieve all alert configurations for a specific website.

        Use this to fetch all alert configurations associated with a website,
        optionally filtered by specific alert IDs.
        """
        return f"""
        Retrieve all website alert configurations for website ID: {website_id}.
        Parameters:
        - website_id: {website_id}
        - alert_ids: {alert_ids if alert_ids is not None else 'None (fetch all)'}
        """

    @auto_register_prompt
    @staticmethod
    def find_website_alert_config(
        id: str,
        valid_on: Optional[int] = None
    ) -> str:
        """
        Retrieve a specific website alert configuration by ID.

        Use this to fetch a single configuration by its alert config ID,
        optionally at a specific point in time.
        """
        return f"""
        Retrieve website alert configuration by ID.
        Parameters:
        - id: {id}
        - valid_on: {valid_on if valid_on is not None else 'None (latest version)'}
        """

    @classmethod
    def get_prompts(cls):
        return [
            ('find_active_website_alert_configs', cls.find_active_website_alert_configs),
            ('find_website_alert_config', cls.find_website_alert_config),
        ]
