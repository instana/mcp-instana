"""Tests for the EventsPrompts class."""
import unittest
from unittest.mock import patch

from src.prompts import PROMPT_REGISTRY
from src.prompts.events.events_tools import EventsPrompts


class TestEventsPrompts(unittest.TestCase):
    """Test cases for the EventsPrompts class."""

    def test_get_event_registered(self):
        """Test that get_event is registered in the prompt registry."""
        # The registry contains staticmethod objects, so we need to unwrap them
        func = EventsPrompts.get_event
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_kubernetes_info_events_registered(self):
        """Test that get_kubernetes_info_events is registered in the prompt registry."""
        func = EventsPrompts.get_kubernetes_info_events
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_agent_monitoring_events_registered(self):
        """Test that get_agent_monitoring_events is registered in the prompt registry."""
        func = EventsPrompts.get_agent_monitoring_events
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_events_by_severity_and_state_registered(self):
        """Test that get_events_by_severity_and_state is registered in the prompt registry."""
        func = EventsPrompts.get_events_by_severity_and_state
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_events_by_entity_and_problem_registered(self):
        """Test that get_events_by_entity_and_problem is registered in the prompt registry."""
        func = EventsPrompts.get_events_by_entity_and_problem
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = EventsPrompts.get_prompts()
        # There are now 7 prompts in the EventsPrompts class
        self.assertEqual(len(prompts), 7)
        self.assertEqual(prompts[0][0], 'get_event')
        self.assertEqual(prompts[1][0], 'get_kubernetes_info_events')
        self.assertEqual(prompts[2][0], 'get_agent_monitoring_events')
        self.assertEqual(prompts[3][0], 'get_events_by_severity_and_state')
        self.assertEqual(prompts[4][0], 'get_events_by_entity_and_problem')

    def test_get_event_prompt_content(self):
        """Test that get_event returns expected prompt content."""
        result = EventsPrompts.get_event(event_id="event-123")
        self.assertIn("Get specific event", result)
        self.assertIn("event-123", result)

    def test_get_kubernetes_info_events_prompt_content(self):
        """Test that get_kubernetes_info_events returns expected prompt content."""
        result = EventsPrompts.get_kubernetes_info_events(
            from_time=1000, to_time=2000, time_range="1h", max_events=100
        )
        self.assertIn("Get Kubernetes info events", result)
        self.assertIn("1000", result)
        self.assertIn("2000", result)
        self.assertIn("1h", result)
        self.assertIn("100", result)

    def test_get_agent_monitoring_events_prompt_content(self):
        """Test that get_agent_monitoring_events returns expected prompt content."""
        result = EventsPrompts.get_agent_monitoring_events(
            query="test", from_time=1000, to_time=2000, size=50, max_events=25
        )
        self.assertIn("Get Agent monitoring events", result)
        self.assertIn("test", result)
        self.assertIn("1000", result)
        self.assertIn("50", result)

    def test_get_events_by_severity_and_state_prompt_content(self):
        """Test that get_events_by_severity_and_state returns expected prompt content."""
        result = EventsPrompts.get_events_by_severity_and_state(
            from_time=1000, to_time=2000, state="open", severity=5, max_events=50
        )
        self.assertIn("Get events", result)
        self.assertIn("1000", result)
        self.assertIn("open", result)
        self.assertIn("5", result)

    def test_get_events_by_entity_and_problem_prompt_content(self):
        """Test that get_events_by_entity_and_problem returns expected prompt content."""
        result = EventsPrompts.get_events_by_entity_and_problem(
            time_range="1h", entity_name="test-entity", problem="high error rate"
        )
        self.assertIn("Get events", result)
        self.assertIn("1h", result)
        self.assertIn("test-entity", result)
        self.assertIn("high error rate", result)

    def test_get_events_by_entity_type_and_event_type_prompt_content(self):
        """Test that get_events_by_entity_type_and_event_type returns expected prompt content."""
        result = EventsPrompts.get_events_by_entity_type_and_event_type(
            time_range="1d", entity_type="application", event_type_filters=["INCIDENT"]
        )
        self.assertIn("Get events", result)
        self.assertIn("1d", result)
        self.assertIn("application", result)

    def test_get_events_by_ids_prompt_content(self):
        """Test that get_events_by_ids returns expected prompt content."""
        result = EventsPrompts.get_events_by_ids(event_ids=["event-1", "event-2"])
        self.assertIn("Get events by IDs", result)
        self.assertIn("event-1", result)

    def test_get_events_by_ids_with_string(self):
        """Test that get_events_by_ids works with string input."""
        result = EventsPrompts.get_events_by_ids(event_ids="event-123")
        self.assertIn("Get events by IDs", result)
        self.assertIn("event-123", result)

    def test_all_prompts_return_strings(self):
        """Test that all prompt methods return strings."""
        prompts = EventsPrompts.get_prompts()
        for name, prompt_func in prompts:
            if name == "get_event":
                result = prompt_func(event_id="test")
            elif name in {"get_kubernetes_info_events", "get_agent_monitoring_events", "get_events_by_severity_and_state", "get_events_by_entity_and_problem", "get_events_by_entity_type_and_event_type"}:
                result = prompt_func()
            elif name == "get_events_by_ids":
                result = prompt_func(event_ids=["test"])

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_class_is_instantiable(self):
        """Test that the class can be instantiated."""
        instance = EventsPrompts()
        self.assertIsInstance(instance, EventsPrompts)

    def test_get_events_by_entity_type_and_event_type_registered(self):
        """Test that get_events_by_entity_type_and_event_type is registered."""
        func = EventsPrompts.get_events_by_entity_type_and_event_type
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))

    def test_get_events_by_ids_registered(self):
        """Test that get_events_by_ids is registered."""
        func = EventsPrompts.get_events_by_ids
        self.assertTrue(any(
            getattr(item, '__func__', item) == func
            for item in PROMPT_REGISTRY
        ))


if __name__ == '__main__':
    unittest.main()
