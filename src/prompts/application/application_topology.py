from typing import Optional

from src.prompts import auto_register_prompt


class ApplicationTopologyPrompts:
    """Class containing application topology related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_application_topology(
        window_size: Optional[int] = None,
        to_timestamp: Optional[int] = None,
        application_id: Optional[str] = None,
        application_boundary_scope: Optional[str] = None) -> str:
        """Retrieve the service topology showing connections between services"""
        return f"""
        Get application topology:
        - Window size: {window_size or '1 hour'}
        - To timestamp: {to_timestamp or 'current time'}
        - Application ID: {application_id or 'None'}
        - Boundary scope: {application_boundary_scope or 'INBOUND'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_application_topology', cls.get_application_topology),
        ]
