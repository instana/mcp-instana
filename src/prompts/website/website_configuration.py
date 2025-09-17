from typing import Optional, Union

from src.prompts import auto_register_prompt


class WebsiteConfigurationPrompts:
    """Class containing website configuration related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_websites() -> str:
        """Retrieve all configured websites in your Instana environment"""
        return """
        Get all websites to see configured website monitoring setups.
        """

    @auto_register_prompt
    @staticmethod
    def get_website(website_id: str) -> str:
        """Retrieve configuration details for a specific website"""
        return f"""
        Get website configuration:
        - Website ID: {website_id}
        """

    @auto_register_prompt
    @staticmethod
    def create_website(payload: Union[dict, str]) -> str:
        """Create a new website configuration in your Instana environment"""
        return f"""
        Create website with configuration:
        - Payload: {payload}
        """

    @auto_register_prompt
    @staticmethod
    def delete_website(website_id: str) -> str:
        """Delete a website configuration from your Instana environment"""
        return f"""
        Delete website:
        - Website ID: {website_id}
        """

    @auto_register_prompt
    @staticmethod
    def rename_website(website_id: str, payload: Union[dict, str]) -> str:
        """Rename a website configuration in your Instana environment"""
        return f"""
        Rename website:
        - Website ID: {website_id}
        - Rename payload: {payload}
        """

    @auto_register_prompt
    @staticmethod
    def get_website_geo_location_configuration(website_id: str) -> str:
        """Retrieve geo-location configuration for a specific website"""
        return f"""
        Get website geo-location configuration:
        - Website ID: {website_id}
        """

    @auto_register_prompt
    @staticmethod
    def update_website_geo_location_configuration(website_id: str, payload: Union[dict, str]) -> str:
        """Update geo-location configuration for a specific website"""
        return f"""
        Update website geo-location configuration:
        - Website ID: {website_id}
        - Configuration payload: {payload}
        """

    @auto_register_prompt
    @staticmethod
    def get_website_ip_masking_configuration(website_id: str) -> str:
        """Retrieve IP masking configuration for a specific website"""
        return f"""
        Get website IP masking configuration:
        - Website ID: {website_id}
        """

    @auto_register_prompt
    @staticmethod
    def update_website_ip_masking_configuration(website_id: str, payload: Union[dict, str]) -> str:
        """Update IP masking configuration for a specific website"""
        return f"""
        Update website IP masking configuration:
        - Website ID: {website_id}
        - Configuration payload: {payload}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_websites', cls.get_websites),
            ('get_website', cls.get_website),
            ('create_website', cls.create_website),
            ('delete_website', cls.delete_website),
            ('rename_website', cls.rename_website),
            ('get_website_geo_location_configuration', cls.get_website_geo_location_configuration),
            ('update_website_geo_location_configuration', cls.update_website_geo_location_configuration),
            ('get_website_ip_masking_configuration', cls.get_website_ip_masking_configuration),
            ('update_website_ip_masking_configuration', cls.update_website_ip_masking_configuration),
        ]
