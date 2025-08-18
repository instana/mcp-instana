from typing import Optional

from src.prompts import auto_register_prompt


class InfrastructureCatalogPrompts:
    """Class containing infrastructure catalog related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_available_payload_keys_by_plugin_id(plugin_id: str) -> str:
        """Retrieve available payload keys for a specific plugin"""
        return f"Get payload keys for plugin ID: {plugin_id}"

    @auto_register_prompt
    @staticmethod
    def get_infrastructure_catalog_metrics(plugin: str, filter: Optional[str] = None) -> str:
        """
        Get the list of available metrics for a specified plugin, supporting metric exploration for dashboards and queries.

        Args:
            plugin (str): Plugin (e.g., host, JVM, Kubernetes)
            filter (Optional[str], optional): Filter string for narrowing down metrics
        """
        return f"""
        Get infrastructure catalog metrics:
        - Plugin: {plugin}
        - Filter: {filter or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_tag_catalog(plugin: str) -> str:
        """Get available tags for a specific plugin"""
        return f"Get tag catalog for plugin: {plugin}"

    @auto_register_prompt
    @staticmethod
    def get_tag_catalog_all() -> str:
        """Retrieve the complete list of tags available across all monitored entities"""
        return "Get all tag catalogs"

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_available_payload_keys_by_plugin_id', cls.get_available_payload_keys_by_plugin_id),
            ('get_infrastructure_catalog_metrics', cls.get_infrastructure_catalog_metrics),
            ('get_tag_catalog', cls.get_tag_catalog),
            ('get_tag_catalog_all', cls.get_tag_catalog_all),
        ]


