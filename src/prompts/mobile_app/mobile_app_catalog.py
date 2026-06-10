from src.prompts import auto_register_prompt


class MobileAppCatalogPrompts:
    """Class containing mobile app catalog related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_mobile_app_tag_catalog() -> str:
        """Retrieve mobile app monitoring tag names filtered by beacon type and use case"""
        return """
        Get mobile app tag names for specific beacon type (SESSION_START, HTTP_REQUEST, etc.) and use case (GROUPING, FILTERING, etc.).
        """

    @auto_register_prompt
    @staticmethod
    def get_mobile_app_metric_catalog() -> str:
        """Retrieve all available metric definitions for mobile app monitoring to discover what metrics are available"""
        return """
        Get mobile app metric catalog to discover available mobile app monitoring metrics.
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_mobile_app_tag_catalog', cls.get_mobile_app_tag_catalog),
            ('get_mobile_app_metric_catalog', cls.get_mobile_app_metric_catalog),
        ]
