from typing import Optional

from src.prompts import auto_register_prompt


class InfrastructureTopologyPrompts:
    """Class containing infrastructure topology related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_related_hosts(
        snapshot_id: str,
        to_time: Optional[int] = None,
        window_size: Optional[int] = None
    ) -> str:
        """Get hosts related to a specific snapshot"""
        return f"""
        Get related hosts:
        - Snapshot ID: {snapshot_id}
        - To time: {to_time or '1 hour'}
        - Window size: {window_size or '1 hour'}
        """

    @auto_register_prompt
    @staticmethod
    def get_topology(include_data: Optional[bool] = False) -> str:
        """Retrieve the complete infrastructure topology"""
        return f"Get complete topology with include_data: {include_data or 'False'}"

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_related_hosts', cls.get_related_hosts),
            ('get_topology', cls.get_topology),
        ]


