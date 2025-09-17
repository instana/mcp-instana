from typing import Optional

from src.prompts import auto_register_prompt


class WebsiteCatalogPrompts:
    """Class containing website catalog related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_website_catalog_metrics() -> str:
        """Retrieve all available metric definitions for website monitoring to discover what metrics are available"""
        return """
        Get website catalog metrics to discover available website monitoring metrics.
        """

    @auto_register_prompt
    @staticmethod
    def get_website_catalog_tags() -> str:
        """Retrieve all available tags for website monitoring to discover what tags are available for filtering beacons"""
        return """
        Get website catalog tags to discover available website monitoring tags for filtering.
        """

    @auto_register_prompt
    @staticmethod
    def get_website_tag_catalog() -> str:
        """Retrieve all available tags for website monitoring to discover what tags are available for filtering beacons"""
        return """
        Get website tag catalog to discover available website monitoring tags for filtering.
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_website_catalog_metrics', cls.get_website_catalog_metrics),
            ('get_website_catalog_tags', cls.get_website_catalog_tags),
            ('get_website_tag_catalog', cls.get_website_tag_catalog),
        ]
