from typing import Optional

from src.prompts import auto_register_prompt


class ApplicationCatalogPrompts:
    """Class containing application catalog related prompts"""

    @auto_register_prompt
    @staticmethod
    def app_catalog_yesterday(limit: int, use_case: Optional[str] = None, data_source: Optional[str] = None, var_from: Optional[int] = None) -> str:
        """List 3 available application tag catalog data for yesterday"""
        return f"""
        Get application catalog data:
        - Use case: {use_case or 'None'}
        - Data source: {data_source or 'None'}
        - From: {var_from or 'last 24 hours'}
        - Limit: {limit or '100'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('app_catalog_yesterday', cls.app_catalog_yesterday),
        ]
