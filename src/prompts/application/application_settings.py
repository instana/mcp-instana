from typing import Optional

from src.prompts import auto_register_prompt


class ApplicationSettingsPrompts:
    """Class containing application settings related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_all_applications_configs() -> str:
        """Get a list of all Application Perspectives with their configuration settings"""
        return "Retrieve all application configurations"

    @auto_register_prompt
    @staticmethod
    def get_application_config(id: str) -> str:
        """Get an Application Perspective configuration by ID"""
        return f"Retrieve application configuration with ID: {id}"

    @auto_register_prompt
    @staticmethod
    def get_all_endpoint_configs() -> str:
        """Get a list of all Endpoint Perspectives with their configuration settings"""
        return "Retrieve all endpoint configurations"

    @auto_register_prompt
    @staticmethod
    def get_endpoint_config(id: str) -> str:
        """Retrieve the endpoint configuration of a service"""
        return f"Get endpoint configuration with ID: {id}"

    @auto_register_prompt
    @staticmethod
    def get_all_manual_service_configs() -> str:
        """Get a list of all Manual Service Perspectives with their configuration settings"""
        return "Retrieve all manual service configurations"

    @auto_register_prompt
    @staticmethod
    def add_manual_service_config(
        enabled: bool,
        tag_filter_expression: dict,
        unmonitored_service_name: Optional[str] = None,
        existing_service_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """Create a manual service mapping configuration"""
        return f"""
        Add manual service configuration:
        - Tag filter: {tag_filter_expression}
        - Unmonitored service name: {unmonitored_service_name or 'None'}
        - Existing service ID: {existing_service_id or 'None'}
        - Description: {description or 'None'}
        - Enabled: {enabled or 'True'}
        """

    @auto_register_prompt
    @staticmethod
    def get_service_config(id: str) -> str:
        """Retrieve the particular custom service configuration"""
        return f"Get service configuration with ID: {id}"

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_all_applications_configs', cls.get_all_applications_configs),
            ('get_application_config', cls.get_application_config),
            ('get_all_endpoint_configs', cls.get_all_endpoint_configs),
            ('get_endpoint_config', cls.get_endpoint_config),
            ('get_all_manual_service_configs', cls.get_all_manual_service_configs),
            ('add_manual_service_config', cls.add_manual_service_config),
            ('get_service_config', cls.get_service_config),
        ]
