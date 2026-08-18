from src.prompts import auto_register_prompt


class SyntheticCatalogPrompts:
    """Class containing synthetic catalog related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_synthetic_catalog_metrics() -> str:
        """Retrieve metric definitions with metadata: metricId, label, description, unit/formatter, aggregations, beaconTypes, and more"""
        return """
        Get synthetic catalog metrics with necessary metadata for query planning, including descriptions, supported aggregations, and beacon types.
        """

    @auto_register_prompt
    @staticmethod
    def get_synthetic_tag_catalog() -> str:
        """Retrieve synthetic monitoring tag names filtered by beacon type and use case"""
        return """
        Get complete list of all synthetic monitoring tags available.
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_synthetic_catalog_metrics', cls.get_synthetic_catalog_metrics),
            ('get_synthetic_tag_catalog', cls.get_synthetic_tag_catalog),
        ]
