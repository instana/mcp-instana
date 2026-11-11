"""Prompts for Alert Channels management."""

from typing import Optional

from src.prompts import auto_register_prompt


class AlertChannelsPrompts:
    """Class containing alert channels related prompts."""

    @auto_register_prompt
    @staticmethod
    def get_alert_channels_overview(
        kind: Optional[str] = None,
        name_filter: Optional[str] = None,
    ) -> str:
        """List summary overview of all alerting channels with optional kind or name filtering."""
        return f"""
        List alert channels overview:
        - Channel type / kind filter: {kind or '(all kinds)'}
        - Name filter: {name_filter or '(none)'}

        Use manage_alert_channels with operation='get_overview' to discover channel IDs and summaries.
        """

    @auto_register_prompt
    @staticmethod
    def get_alert_channel(
        id: Optional[str] = None,
        name: Optional[str] = None,
    ) -> str:
        """Get full configuration details of a specific alert channel by ID or name."""
        return f"""
        Get alert channel details:
        - Channel ID: {id or '(not specified)'}
        - Channel Name: {name or '(not specified)'}

        Use manage_alert_channels with operation='get' and provide either 'id' or 'name'.
        All sensitive secrets in the response will be automatically masked.
        """

    @auto_register_prompt
    @staticmethod
    def find_alert_channel_by_name(name: str) -> str:
        """Find an alert channel by name and inspect its configuration."""
        return f"""
        Find and inspect alert channel by name:
        - Target channel name: {name}

        Steps:
        1. Call manage_alert_channels with operation='get', params={{"name": "{name}"}}
        2. If multiple candidates match, choose the intended channel ID from the candidates list.
        3. Inspect the returned masked configuration (webhook URLs, receivers, headers, or team scoping).
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class."""
        return [
            ("get_alert_channels_overview", cls.get_alert_channels_overview),
            ("get_alert_channel", cls.get_alert_channel),
            ("find_alert_channel_by_name", cls.find_alert_channel_by_name),
        ]
