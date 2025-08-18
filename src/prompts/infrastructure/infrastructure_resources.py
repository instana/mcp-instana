from typing import Optional

from src.prompts import auto_register_prompt


class InfrastructureResourcesPrompts:
    """Class containing infrastructure resources related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_infrastructure_monitoring_state() -> str:
        """Get an overview of the current Instana monitoring state"""
        return "Get infrastructure monitoring state"

    @auto_register_prompt
    @staticmethod
    def get_infrastructure_plugin_payload(
        snapshot_id: str,
        payload_key: str,
        to_time: Optional[int] = None,
        window_size: Optional[int] = None
    ) -> str:
        """Get raw plugin payload data for a specific snapshot entity"""
        return f"""
        Get plugin payload:
        - Snapshot ID: {snapshot_id}
        - Payload key: {payload_key}
        - To time: {to_time or 'current time'}
        - Window size: {window_size or '1 hour'}
        """

    @auto_register_prompt
    @staticmethod
    def get_infrastructure_metrics_snapshot(
        snapshot_id: str,
        to_time: Optional[int] = None,
        window_size: Optional[int] = None
    ) -> str:
        """Get detailed information for a single infrastructure snapshot"""
        return f"""
        Get infrastructure snapshot:
        - Snapshot ID: {snapshot_id}
        - To time: {to_time or 'current time'}
        - Window size: {window_size or '1 hour'}
        """

    @auto_register_prompt
    @staticmethod
    def post_infrastructure_metrics_snapshot(
        snapshot_ids: list[str],
        to_time: Optional[int] = None,
        window_size: Optional[int] = None,
        detailed: Optional[bool] = False,
    ) -> str:
        """Fetch details of multiple snapshots by their IDs"""
        return f"""
        Get multiple infrastructure snapshots:
        - Snapshot IDs: {snapshot_ids}
        - To time: {to_time or 'current time'}
        - Window size: {window_size or '1 hour'}
        - Detailed: {detailed or 'False'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_infrastructure_monitoring_state', cls.get_infrastructure_monitoring_state),
            ('get_infrastructure_plugin_payload', cls.get_infrastructure_plugin_payload),
            ('get_infrastructure_metrics_snapshot', cls.get_infrastructure_metrics_snapshot),
            ('post_infrastructure_metrics_snapshot', cls.post_infrastructure_metrics_snapshot),
        ]


