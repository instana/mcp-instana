from typing import Optional, Union

from src.prompts import auto_register_prompt


class MobileAppConfigurationPrompts:
    """Class containing mobile app configuration related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_all_mobile_apps() -> str:
        """Retrieve all configured mobile apps in your Instana environment"""
        return """
        Get all mobile apps to see configured mobile app monitoring setups.
        """

    @auto_register_prompt
    @staticmethod
    def get_mobile_app_by_id(mobile_app_id: str) -> str:
        """Retrieve configuration details for a specific mobile app"""
        return f"""
        Get mobile app configuration:
        - Mobile App ID: {mobile_app_id}
        """

    @auto_register_prompt
    @staticmethod
    def get_mobile_app_geo_location_configuration(mobile_app_id: str) -> str:
        """Retrieve geo-location configuration for a specific mobile app"""
        return f"""
        Get mobile app geo-location configuration:
        - Mobile App ID: {mobile_app_id}
        """

    @auto_register_prompt
    @staticmethod
    def get_mobile_app_geo_mapping_rules(mobile_app_id: str) -> str:
        """Retrieve geo-location mapping rules for a specific mobile app"""
        return f"""
        Get mobile app geo-location mapping rules:
        - Mobile App ID: {mobile_app_id}
        """

    @auto_register_prompt
    @staticmethod
    def get_mobile_app_ip_masking_configuration(mobile_app_id: str) -> str:
        """Retrieve IP masking configuration for a specific mobile app"""
        return f"""
        Get mobile app IP masking configuration:
        - Mobile App ID: {mobile_app_id}
        """

    @auto_register_prompt
    @staticmethod
    def get_all_mobile_app_source_map_upload_configurations(mobile_app_id: str) -> str:
        """Retrieve all source map upload configurations for a specific mobile app"""
        return f"""
        Get all source map upload configurations for mobile app:
        - Mobile App ID: {mobile_app_id}
        """

    @auto_register_prompt
    @staticmethod
    def get_mobile_app_source_map_upload_configuration_by_id(mobile_app_id: str, config_id: str) -> str:
        """Retrieve details of a specific source map upload configuration for a specific mobile app"""
        return f"""
        Get source map upload configuration details:
        - Mobile App ID: {mobile_app_id}
        - Configuration ID: {config_id}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_all_mobile_apps', cls.get_all_mobile_apps),
            ('get_mobile_app_by_id', cls.get_mobile_app_by_id),
            ('get_mobile_app_geo_location_configuration', cls.get_mobile_app_geo_location_configuration),
            ('get_mobile_app_geo_mapping_rules', cls.get_mobile_app_geo_mapping_rules),
            ('get_mobile_app_ip_masking_configuration', cls.get_mobile_app_ip_masking_configuration),
            ('get_all_mobile_app_source_map_upload_configurations', cls.get_all_mobile_app_source_map_upload_configurations),
            ('get_mobile_app_source_map_upload_configuration_by_id', cls.get_mobile_app_source_map_upload_configuration_by_id),
        ]
