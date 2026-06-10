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
    def get_events_by_severity_and_state(
        from_time: Optional[int] = None,
        to_time: Optional[int] = None,
        state: Optional[str] = None,
        severity: Optional[int] = None,
        event_type_filters: Optional[list[str]] = None,
        max_events: Optional[int] = 50
    ) -> str:
        """Show me all closed issues with severity higher than 5, group by metrics, for Apr 22 from 10 to 11 am """
        return f"""
        Get events using filters:
        {{
            - From time: {from_time or 1745383800000} (Apr 22, 2025 10:00 AM)
            - To time: {to_time or 1745387400000} (Apr 22, 2025 11:00 AM)
            - State: {state or 'closed'}
            - Severity: {severity or 10} (critical)
            - Event type filters: {event_type_filters or '["ISSUE"]'}
            - Max events: {max_events}
        }}
        """

    @auto_register_prompt
    @staticmethod
    def get_events_by_entity_and_problem(
        time_range: Optional[str] = None,
        entity_name: Optional[str] = None,
        problem: Optional[str] = None,
        event_type_filters: Optional[list[str]] = None,
        max_events: Optional[int] = 50
    ) -> str:
        """Show me details for CRI-O Container issues generated in the last 45 min that had "high error rate" problem"""
        return f"""
        Get events:
        {{
            - Time range: {time_range or 'last 45 minutes'}
            - Entity name: {entity_name or 'CRI-O Container'}
            - Problem: {problem or 'high error rate'}
            - Event type filters: {event_type_filters or '["ISSUE"]'}
            - Max events: {max_events}
        }}
        """

    @auto_register_prompt
    @staticmethod
    def get_events_by_entity_type_and_event_type(
        time_range: Optional[str] = None,
        entity_type: Optional[str] = None,
        event_type_filters: Optional[list[str]] = None,
        max_events: Optional[int] = 50
    ) -> str:
        """Show me application incidents from the last week grouped by problem and sorted by severity"""
        return f"""
        Get events:
        {{
            - Time range: {time_range or 'last week'}
            - Entity type: {entity_type or 'application'}
            - Event type filters: {event_type_filters or '["INCIDENT"]'}
            - Max events: {max_events}
        }}
        """

    @auto_register_prompt
    @staticmethod
    def get_events_by_ids(
        event_ids: list[str] | str
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
            ('get_events_by_severity_and_state', cls.get_events_by_severity_and_state),
            ('get_events_by_entity_and_problem', cls.get_events_by_entity_and_problem),
            ('get_events_by_entity_type_and_event_type', cls.get_events_by_entity_type_and_event_type),
            ('get_events_by_ids', cls.get_events_by_ids),
        ]
