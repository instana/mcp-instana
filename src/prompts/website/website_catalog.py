from typing import Optional

from src.prompts import auto_register_prompt


class WebsiteCatalogPrompts:
    """Class containing website catalog related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_website_catalog_metrics() -> str:
        """Retrieve metric definitions with metadata: metricId, label, description, unit/formatter, aggregations, beaconTypes, and more"""
        return """
        Get website catalog metrics with necessary metadata for query planning, including descriptions, supported aggregations, and beacon types.
        """

    @auto_register_prompt
    @staticmethod
    def get_website_catalog_tags() -> str:
        """Retrieve all available website monitoring tags across all beacon types"""
        return """
        Get complete list of all website monitoring tags available.
        """

    @auto_register_prompt
    @staticmethod
    def get_website_tag_catalog() -> str:
        """Retrieve website monitoring tag names filtered by beacon type and use case"""
        return """
        Get website tag names for specific beacon type (PAGELOAD, ERROR, etc.) and use case (GROUPING, FILTERING, etc.).
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_website_catalog_metrics', cls.get_website_catalog_metrics),
            ('get_website_catalog_tags', cls.get_website_catalog_tags),
            ('get_website_tag_catalog', cls.get_website_tag_catalog),
        ]
