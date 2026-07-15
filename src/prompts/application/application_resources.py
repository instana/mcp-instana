from typing import Optional

from src.prompts import auto_register_prompt


class ApplicationResourcesPrompts:
    """Class containing application resources related prompts"""

    @auto_register_prompt
    @staticmethod
    def application_insights_summary(window_size: int, to_time: int, name_filter: Optional[str] = None, application_boundary_scope: Optional[str] = None) -> str:
        """Retrieve a list of services within application perspectives from Instana"""
        return f"""
        Get application insights summary with:
        - Name filter: {name_filter or 'None'}
        - Window size: {window_size or '1 hour'}
        - To time: {to_time or 'now'}
        - Boundary scope: {application_boundary_scope or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_applications(name_filter: Optional[str] = None, application_boundary_scope: Optional[str] = None) -> str:
        """Return a list of applications for the given filter and boundary scope"""
        return f"""
        Get application perspectives with:
        - Name filter: {name_filter or 'None'}
        - Boundary scope: {application_boundary_scope or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_services(name_filter: Optional[str] = None, include_snapshot_ids: Optional[bool] = None) -> str:
        """Return a list of services filtered by name and snapshot option"""
        return f"""
        Get application services with:
        - Name filter: {name_filter or 'None'}
        - Include snapshot IDs: {include_snapshot_ids if include_snapshot_ids is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_application_services(
        application_id: Optional[str] = None,
        service_id: Optional[str] = None,
        name_filter: Optional[str] = None,
        application_boundary_scope: Optional[str] = None,
        include_snapshot_ids: Optional[bool] = None,
    ) -> str:
        """Return services for a specific application, with optional filtering"""
        return f"""
        Get services for application:
        - Application ID: {application_id or 'None'}
        - Service ID: {service_id or 'None'}
        - Name filter: {name_filter or 'None'}
        - Boundary scope: {application_boundary_scope or 'None'}
        - Include snapshot IDs: {include_snapshot_ids if include_snapshot_ids is not None else 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_application_endpoints(
        application_id: Optional[str] = None,
        service_id: Optional[str] = None,
        endpoint_id: Optional[str] = None,
        name_filter: Optional[str] = None,
        types: Optional[list] = None,
        technologies: Optional[list] = None,
        application_boundary_scope: Optional[str] = None,
    ) -> str:
        """Return endpoints for a given application/service combination"""
        return f"""
        Get application endpoints with:
        - Application ID: {application_id or 'None'}
        - Service ID: {service_id or 'None'}
        - Endpoint ID: {endpoint_id or 'None'}
        - Name filter: {name_filter or 'None'}
        - Types: {types or 'None'}
        - Technologies: {technologies or 'None'}
        - Boundary scope: {application_boundary_scope or 'None'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('application_insights_summary', cls.application_insights_summary),
            ('get_applications', cls.get_applications),
            ('get_services', cls.get_services),
            ('get_application_services', cls.get_application_services),
            ('get_application_endpoints', cls.get_application_endpoints),
        ]
