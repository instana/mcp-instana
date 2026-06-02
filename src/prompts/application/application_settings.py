from typing import Optional

from src.prompts import auto_register_prompt


class ApplicationSettingsPrompts:
    """Class containing application settings related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_all_applications_configs() -> str:
        """What applications are being monitored right now"""
        return "Retrieve all application configurations"

    @auto_register_prompt
    @staticmethod
    def get_application_config(id: str) -> str:
        """Get an Application Perspective configuration by ID"""
        return f"Retrieve application configuration with ID: {id}"

    @auto_register_prompt
    @staticmethod
    def create_application_config(
        label: str,
        scope: Optional[str] = None,
        boundary_scope: Optional[str] = None,
        access_rules: Optional[str] = None,
        tag_filter_expression: Optional[dict] = None
    ) -> str:
        """
        Create a new Application Perspective configuration with user-provided settings.

        REQUIRED:
        - label: Application perspective name (string)

        OPTIONAL (will prompt user if not provided):
        - scope: Monitoring scope
          Options: "INCLUDE_ALL_DOWNSTREAM" (default), "INCLUDE_IMMEDIATE_DOWNSTREAM_DATABASE_AND_MESSAGING", "INCLUDE_NO_DOWNSTREAM"
        - boundary_scope: Boundary scope
          Options: "ALL" (default), "INBOUND", "DEFAULT"
        - access_rules: Access control rules
          Options: "READ_WRITE_GLOBAL" (default), "READ_ONLY_GLOBAL", "CUSTOM"
        - tag_filter_expression: Tag filter to match services (optional)

        ELICITATION QUESTIONS:
        1. What scope should be used for monitoring? (INCLUDE_ALL_DOWNSTREAM/INCLUDE_IMMEDIATE_DOWNSTREAM_DATABASE_AND_MESSAGING/INCLUDE_NO_DOWNSTREAM)
        2. What boundary scope should be applied? (ALL/INBOUND/DEFAULT)
        3. What access rules should be configured? (READ_WRITE_GLOBAL/READ_ONLY_GLOBAL/CUSTOM)
        4. Do you want to add a tag filter expression to match specific services? (yes/no)

        Example with all options:
        {
            "label": "My Application",
            "scope": "INCLUDE_ALL_DOWNSTREAM",
            "boundaryScope": "ALL",
            "accessRules": [{"accessType": "READ_WRITE", "relationType": "GLOBAL"}],
            "tagFilterExpression": {
                "type": "TAG_FILTER",
                "name": "service.name",
                "operator": "CONTAINS",
                "entity": "DESTINATION",
                "value": "my-service"
            }
        }
        """
        config_details = [f"label: {label}"]
        if scope:
            config_details.append(f"scope: {scope}")
        if boundary_scope:
            config_details.append(f"boundaryScope: {boundary_scope}")
        if access_rules:
            config_details.append(f"accessRules: {access_rules}")
        if tag_filter_expression:
            config_details.append(f"tagFilterExpression: {tag_filter_expression}")

        return f"Create application perspective configuration with {', '.join(config_details)}"

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
            ('create_application_config', cls.create_application_config),
            ('get_all_endpoint_configs', cls.get_all_endpoint_configs),
            ('get_endpoint_config', cls.get_endpoint_config),
            ('get_all_manual_service_configs', cls.get_all_manual_service_configs),
            ('add_manual_service_config', cls.add_manual_service_config),
            ('get_service_config', cls.get_service_config),
        ]
