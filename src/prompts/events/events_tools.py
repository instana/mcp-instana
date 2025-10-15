from typing import List, Optional, Union

from src.prompts import auto_register_prompt


class EventsPrompts:
    """Class containing events related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_event(
        event_id: str
    ) -> str:
        """Get an overview of a specific event"""
        return f"""
        Get specific event:
        - Event ID: {event_id}
        """

    @auto_register_prompt
    @staticmethod
    def get_kubernetes_info_events(
        from_time: Optional[int] = None,
        to_time: Optional[int] = None,
        time_range: Optional[str] = None,
        max_events: Optional[int] = 50
    ) -> str:
        """Get Kubernetes info events and analyze them"""
        return f"""
        Get Kubernetes info events:
        - From time: {from_time or '(default: 24 hours ago)'}
        - To time: {to_time or '(default: current time)'}
        - Time range: {time_range or '(not specified)'}
        - Max events: {max_events}
        """

    @auto_register_prompt
    @staticmethod
    def get_agent_monitoring_events(
        query: Optional[str] = None,
        from_time: Optional[int] = None,
        to_time: Optional[int] = None,
        size: Optional[int] = 100,
        max_events: Optional[int] = 50,
        time_range: Optional[str] = None
    ) -> str:
        """Get Agent monitoring events and analyze them"""
        return f"""
        Get Agent monitoring events:
        - Query: {query or '(not specified)'}
        - From time: {from_time or '(default: 1 hour ago)'}
        - To time: {to_time or '(default: current time)'}
        - Size: {size}
        - Max events: {max_events}
        - Time range: {time_range or '(not specified)'}
        """

    @auto_register_prompt
    @staticmethod
    def get_issues(
        query: Optional[str] = None,
        from_time: Optional[int] = None,
        to_time: Optional[int] = None,
        filter_event_updates: Optional[bool] = None,
        exclude_triggered_before: Optional[int] = None,
        event_type_filters: Optional[list[str]] = None,
        max_events: Optional[int] = 50,
        size: Optional[int] = 100,
        time_range: Optional[str] = None
    ) -> str:
        """Get all issues within a specified time range"""
        return f"""
        Get all events:
        - Query: {query or '(not specified)'}
        - From time: {from_time or '(default: 1 hour ago)'}
        - To time: {to_time or '(default: current time)'}
        - Size: {size}
        - Max events: {max_events}
        - Time range: {time_range or '(not specified)'}
        - Filter event updates: {filter_event_updates or 'False'}
        - Exclude triggered before: {exclude_triggered_before or 'None'}
        - Event type filters: {event_type_filters or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_incidents(
        query: Optional[str] = None,
        from_time: Optional[int] = None,
        to_time: Optional[int] = None,
        filter_event_updates: Optional[bool] = None,
        exclude_triggered_before: Optional[int] = None,
        event_type_filters: Optional[list[str]] = None,
        max_events: Optional[int] = 50,
        size: Optional[int] = 100,
        time_range: Optional[str] = None
    ) -> str:
        """Get all incidents within a specified time range"""
        return f"""
        Get all events:
        - Query: {query or '(not specified)'}
        - From time: {from_time or '(default: 1 hour ago)'}
        - To time: {to_time or '(default: current time)'}
        - Size: {size}
        - Max events: {max_events}
        - Time range: {time_range or '(not specified)'}
        - Filter event updates: {filter_event_updates or 'False'}
        - Exclude triggered before: {exclude_triggered_before or 'None'}
        - Event type filters: {event_type_filters or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_changes(
        query: Optional[str] = None,
        from_time: Optional[int] = None,
        to_time: Optional[int] = None,
        filter_event_updates: Optional[bool] = None,
        exclude_triggered_before: Optional[int] = None,
        event_type_filters: Optional[list[str]] = None,
        max_events: Optional[int] = 50,
        size: Optional[int] = 100,
        time_range: Optional[str] = None
    ) -> str:
        """Get all changes within a specified time range"""
        return f"""
        Get all events:
        - Query: {query or '(not specified)'}
        - From time: {from_time or '(default: 1 hour ago)'}
        - To time: {to_time or '(default: current time)'}
        - Size: {size}
        - Max events: {max_events}
        - Time range: {time_range or '(not specified)'}
        - Filter event updates: {filter_event_updates or 'False'}
        - Exclude triggered before: {exclude_triggered_before or 'None'}
        - Event type filters: {event_type_filters or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_events_by_ids(
        event_ids: Union[List[str], str]
    ) -> str:
        """Get multiple events by their IDs"""
        return f"""
        Get events by IDs:
        - Event IDs: {event_ids}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_event', cls.get_event),
            ('get_kubernetes_info_events', cls.get_kubernetes_info_events),
            ('get_agent_monitoring_events', cls.get_agent_monitoring_events),
            ('get_issues', cls.get_issues),
            ('get_incidents', cls.get_incidents),
            ('get_changes', cls.get_changes),
            ('get_events_by_ids', cls.get_events_by_ids),
        ]
