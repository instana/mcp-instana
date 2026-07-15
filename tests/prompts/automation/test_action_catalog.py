"""Tests for the ActionCatalogPrompts class."""
import sys
import unittest
from unittest.mock import MagicMock

# Mock fastmcp before importing src.prompts
mock_fastmcp = MagicMock()
# Make the prompt decorator return the original function unchanged
mock_fastmcp.FastMCP.return_value.prompt.return_value = lambda func: func
sys.modules['fastmcp'] = mock_fastmcp

from src.prompts import PROMPT_REGISTRY
from src.prompts.automation.action_catalog import ActionCatalogPrompts


class TestActionCatalogPrompts(unittest.TestCase):
    """Test cases for the ActionCatalogPrompts class."""

    def test_get_action_matches_registered(self):
        """Test that get_action_matches is registered in the prompt registry."""
        func = ActionCatalogPrompts.get_action_matches
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_actions_registered(self):
        """Test that get_actions is registered in the prompt registry."""
        func = ActionCatalogPrompts.get_actions
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_action_details_registered(self):
        """Test that get_action_details is registered in the prompt registry."""
        func = ActionCatalogPrompts.get_action_details
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_action_types_registered(self):
        """Test that get_action_types is registered in the prompt registry."""
        func = ActionCatalogPrompts.get_action_types
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_action_tags_registered(self):
        """Test that get_action_tags is registered in the prompt registry."""
        func = ActionCatalogPrompts.get_action_tags
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_action_matches_by_id_and_time_window_registered(self):
        """Test that get_action_matches_by_id_and_time_window is registered in the prompt registry."""
        func = ActionCatalogPrompts.get_action_matches_by_id_and_time_window
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = ActionCatalogPrompts.get_prompts()
        self.assertEqual(len(prompts), 6)
        self.assertEqual(prompts[0][0], 'get_action_matches')
        self.assertEqual(prompts[1][0], 'get_actions')
        self.assertEqual(prompts[2][0], 'get_action_details')
        self.assertEqual(prompts[3][0], 'get_action_types')
        self.assertEqual(prompts[4][0], 'get_action_tags')
        self.assertEqual(prompts[5][0], 'get_action_matches_by_id_and_time_window')

    def test_get_action_matches_prompt_content(self):
        """Test that get_action_matches returns expected prompt content."""
        payload = {"name": "CPU spends significant time waiting for input/output"}
        result = ActionCatalogPrompts.get_action_matches(
            payload=payload,
            target_snapshot_id="snap-123"
        )
        self.assertIn("Get action matches", result)
        self.assertIn(str(payload), result)
        self.assertIn("snap-123", result)

    def test_get_action_matches_prompt_content_no_snapshot(self):
        """Test that get_action_matches returns expected prompt content without snapshot ID."""
        payload = {"name": "Test action"}
        result = ActionCatalogPrompts.get_action_matches(payload=payload)
        self.assertIn("Get action matches", result)
        self.assertIn(str(payload), result)
        self.assertIn("None", result)

    def test_get_actions_prompt_content(self):
        """Test that get_actions returns expected prompt content."""
        result = ActionCatalogPrompts.get_actions()
        self.assertIn("Get all available automation actions", result)
        self.assertIn("action catalog", result)

    def test_get_action_details_prompt_content(self):
        """Test that get_action_details returns expected prompt content."""
        result = ActionCatalogPrompts.get_action_details(action_id="action-123")
        self.assertIn("Get action details", result)
        self.assertIn("action-123", result)

    def test_get_action_types_prompt_content(self):
        """Test that get_action_types returns expected prompt content."""
        result = ActionCatalogPrompts.get_action_types()
        self.assertIn("Get all available action types", result)
        self.assertIn("action catalog", result)

    def test_get_action_tags_prompt_content(self):
        """Test that get_action_tags returns expected prompt content."""
        result = ActionCatalogPrompts.get_action_tags()
        self.assertIn("Get all available action tags", result)
        self.assertIn("action catalog", result)

    def test_get_action_matches_by_id_and_time_window_prompt_content(self):
        """Test that get_action_matches_by_id_and_time_window returns expected prompt content."""
        result = ActionCatalogPrompts.get_action_matches_by_id_and_time_window(
            application_id="app-123",
            snapshot_id="snap-456",
            to=1234567890000,
            window_size=3600000
        )
        self.assertIn("Get action matches by ID and time window", result)
        self.assertIn("app-123", result)
        self.assertIn("snap-456", result)
        self.assertIn("1234567890000", result)
        self.assertIn("3600000", result)

    def test_get_action_matches_by_id_and_time_window_prompt_content_minimal(self):
        """Test that get_action_matches_by_id_and_time_window returns expected prompt content with minimal params."""
        result = ActionCatalogPrompts.get_action_matches_by_id_and_time_window(
            application_id="app-123"
        )
        self.assertIn("Get action matches by ID and time window", result)
        self.assertIn("app-123", result)
        self.assertIn("None", result)


    def test_get_action_matches_with_empty_payload(self):
        """Test get_action_matches with empty payload dict"""
        result = ActionCatalogPrompts.get_action_matches(payload={})
        self.assertIn("Payload: {}", result)
        self.assertIn("None", result)

    def test_get_action_matches_with_complex_payload(self):
        """Test get_action_matches with complex payload"""
        payload = {
            "name": "Test action",
            "filters": {"severity": "critical"},
            "tags": ["production", "database"]
        }
        result = ActionCatalogPrompts.get_action_matches(payload=payload)
        self.assertIn(str(payload), result)

    def test_get_action_details_with_special_chars(self):
        """Test get_action_details with special characters in ID"""
        result = ActionCatalogPrompts.get_action_details(action_id="action-123_test.v2")
        self.assertIn("action-123_test.v2", result)

    def test_get_action_matches_by_id_with_only_application_id(self):
        """Test get_action_matches_by_id_and_time_window with only application_id"""
        result = ActionCatalogPrompts.get_action_matches_by_id_and_time_window(
            application_id="app-123"
        )
        self.assertIn("app-123", result)
        self.assertIn("Snapshot ID: None", result)
        self.assertIn("To timestamp: None", result)
        self.assertIn("Window size: None", result)

    def test_get_action_matches_by_id_with_only_snapshot_id(self):
        """Test get_action_matches_by_id_and_time_window with only snapshot_id"""
        result = ActionCatalogPrompts.get_action_matches_by_id_and_time_window(
            snapshot_id="snap-456"
        )
        self.assertIn("snap-456", result)
        self.assertIn("Application ID: None", result)

    def test_get_action_matches_by_id_with_all_none(self):
        """Test get_action_matches_by_id_and_time_window with all None values"""
        result = ActionCatalogPrompts.get_action_matches_by_id_and_time_window()
        self.assertIn("Application ID: None", result)
        self.assertIn("Snapshot ID: None", result)
        self.assertIn("To timestamp: None", result)
        self.assertIn("Window size: None", result)

    def test_all_prompts_return_strings(self):
        """Test that all prompt methods return strings"""
        prompts = ActionCatalogPrompts.get_prompts()
        for name, prompt_func in prompts:
            if name == "get_action_matches":
                result = prompt_func(payload={})
            elif name == "get_actions":
                result = prompt_func()
            elif name == "get_action_details":
                result = prompt_func(action_id="test")
            elif name in {"get_action_types", "get_action_tags", "get_action_matches_by_id_and_time_window"}:
                result = prompt_func()

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_get_prompts_returns_tuples(self):
        """Test that get_prompts returns list of tuples"""
        prompts = ActionCatalogPrompts.get_prompts()
        for item in prompts:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            self.assertIsInstance(item[0], str)
            self.assertTrue(callable(item[1]))

    def test_prompt_names_are_unique(self):
        """Test that all prompt names are unique"""
        prompts = ActionCatalogPrompts.get_prompts()
        names = [p[0] for p in prompts]
        self.assertEqual(len(names), len(set(names)))

    def test_class_is_instantiable(self):
        """Test that the class can be instantiated"""
        instance = ActionCatalogPrompts()
        self.assertIsInstance(instance, ActionCatalogPrompts)

    def test_prompts_accessible_from_instance(self):
        """Test that prompts are accessible from instance"""
        instance = ActionCatalogPrompts()
        self.assertTrue(hasattr(instance, 'get_action_matches'))
        self.assertTrue(hasattr(instance, 'get_actions'))

    def test_get_action_matches_by_id_with_zero_values(self):
        """Test get_action_matches_by_id_and_time_window with zero values"""
        result = ActionCatalogPrompts.get_action_matches_by_id_and_time_window(
            to=0,
            window_size=0
        )
        # 0 is falsy, so becomes None
        self.assertIn("To timestamp: None", result)
        self.assertIn("Window size: None", result)


if __name__ == '__main__':
    unittest.main()
