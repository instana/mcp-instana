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

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('application_insights_summary', cls.application_insights_summary),
        ]
