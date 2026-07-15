"""Tests for the CustomDashboardPrompts class."""
import sys
import unittest
from unittest.mock import MagicMock

# Mock fastmcp before importing src.prompts
mock_fastmcp = MagicMock()
# Make the prompt decorator return the original function unchanged
mock_fastmcp.FastMCP.return_value.prompt.return_value = lambda func: func
sys.modules['fastmcp'] = mock_fastmcp

from src.prompts import PROMPT_REGISTRY
from src.prompts.settings.custom_dashboard import CustomDashboardPrompts


class TestCustomDashboardPrompts(unittest.TestCase):
    """Test cases for the CustomDashboardPrompts class."""

    def test_create_dashboard_registered(self):
        """Test that create_dashboard is registered in the prompt registry."""
        func = CustomDashboardPrompts.create_dashboard
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_dashboard_list_registered(self):
        """Test that get_dashboard_list is registered in the prompt registry."""
        func = CustomDashboardPrompts.get_dashboard_list
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_dashboard_details_registered(self):
        """Test that get_dashboard_details is registered in the prompt registry."""
        func = CustomDashboardPrompts.get_dashboard_details
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_update_dashboard_registered(self):
        """Test that update_dashboard is registered in the prompt registry."""
        func = CustomDashboardPrompts.update_dashboard
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_delete_dashboard_registered(self):
        """Test that delete_dashboard is registered in the prompt registry."""
        func = CustomDashboardPrompts.delete_dashboard
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_shareable_users_registered(self):
        """Test that get_shareable_users is registered in the prompt registry."""
        func = CustomDashboardPrompts.get_shareable_users
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_shareable_api_tokens_registered(self):
        """Test that get_shareable_api_tokens is registered in the prompt registry."""
        func = CustomDashboardPrompts.get_shareable_api_tokens
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_create_metric_widget_registered(self):
        """Test that create_metric_widget is registered in the prompt registry."""
        func = CustomDashboardPrompts.create_metric_widget
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_create_chart_widget_registered(self):
        """Test that create_chart_widget is registered in the prompt registry."""
        func = CustomDashboardPrompts.create_chart_widget
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_create_application_dashboard_registered(self):
        """Test that create_application_dashboard is registered in the prompt registry."""
        func = CustomDashboardPrompts.create_application_dashboard
        self.assertTrue(
            any(getattr(item, '__func__', item) == func for item in PROMPT_REGISTRY),
            f"{func} not found in PROMPT_REGISTRY"
        )

    def test_get_prompts_returns_all_prompts(self):
        """Test that get_prompts returns all prompts defined in the class."""
        prompts = CustomDashboardPrompts.get_prompts()
        self.assertEqual(len(prompts), 10)
        self.assertEqual(prompts[0][0], 'create_dashboard')
        self.assertEqual(prompts[1][0], 'get_dashboard_list')
        self.assertEqual(prompts[2][0], 'get_dashboard_details')
        self.assertEqual(prompts[3][0], 'update_dashboard')
        self.assertEqual(prompts[4][0], 'delete_dashboard')
        self.assertEqual(prompts[5][0], 'get_shareable_users')
        self.assertEqual(prompts[6][0], 'get_shareable_api_tokens')
        self.assertEqual(prompts[7][0], 'create_metric_widget')
        self.assertEqual(prompts[8][0], 'create_chart_widget')
        self.assertEqual(prompts[9][0], 'create_application_dashboard')

    def test_create_dashboard_prompt_content(self):
        """Test that create_dashboard returns expected prompt content."""
        result = CustomDashboardPrompts.create_dashboard(
            title="Test Dashboard",
            description="A test dashboard",
            widgets=[{"type": "metric", "title": "CPU"}],
            access_rules=[{"accessType": "READ_WRITE", "relationType": "GLOBAL"}],
            tags=["production", "monitoring"]
        )
        self.assertIn("Create a new custom dashboard", result)
        self.assertIn("Title: Test Dashboard", result)
        self.assertIn("Description: A test dashboard", result)
        self.assertIn("Widgets:", result)
        self.assertIn("Access rules:", result)
        self.assertIn("Tags:", result)

    def test_get_dashboard_list_prompt_content(self):
        """Test that get_dashboard_list returns expected prompt content."""
        result = CustomDashboardPrompts.get_dashboard_list(
            limit=50,
            tags=["production"],
            search="monitoring"
        )
        self.assertIn("Get custom dashboards list", result)
        self.assertIn("Limit: 50", result)
        self.assertIn("Tags filter:", result)
        self.assertIn("Search: monitoring", result)

    def test_get_dashboard_details_prompt_content(self):
        """Test that get_dashboard_details returns expected prompt content."""
        result = CustomDashboardPrompts.get_dashboard_details(
            dashboard_id="dashboard-123"
        )
        self.assertIn("Get custom dashboard details", result)
        self.assertIn("Dashboard ID: dashboard-123", result)

    def test_update_dashboard_prompt_content(self):
        """Test that update_dashboard returns expected prompt content."""
        result = CustomDashboardPrompts.update_dashboard(
            dashboard_id="dashboard-123",
            title="Updated Dashboard",
            description="Updated description",
            widgets=[{"type": "chart"}],
            tags=["updated"]
        )
        self.assertIn("Update custom dashboard", result)
        self.assertIn("Dashboard ID: dashboard-123", result)
        self.assertIn("Title: Updated Dashboard", result)
        self.assertIn("Description: Updated description", result)

    def test_delete_dashboard_prompt_content(self):
        """Test that delete_dashboard returns expected prompt content."""
        result = CustomDashboardPrompts.delete_dashboard(
            dashboard_id="dashboard-123"
        )
        self.assertIn("Delete custom dashboard", result)
        self.assertIn("Dashboard ID: dashboard-123", result)

    def test_get_shareable_users_prompt_content(self):
        """Test that get_shareable_users returns expected prompt content."""
        result = CustomDashboardPrompts.get_shareable_users(
            dashboard_id="dashboard-123"
        )
        self.assertIn("Get shareable users for dashboard", result)
        self.assertIn("Dashboard ID: dashboard-123", result)

    def test_get_shareable_api_tokens_prompt_content(self):
        """Test that get_shareable_api_tokens returns expected prompt content."""
        result = CustomDashboardPrompts.get_shareable_api_tokens(
            dashboard_id="dashboard-123"
        )
        self.assertIn("Get shareable API tokens for dashboard", result)
        self.assertIn("Dashboard ID: dashboard-123", result)

    def test_create_metric_widget_prompt_content(self):
        """Test that create_metric_widget returns expected prompt content."""
        result = CustomDashboardPrompts.create_metric_widget(
            title="CPU Usage",
            metric_name="cpu.usage",
            time_range="last 24 hours",
            aggregation="avg",
            filters={"host": "prod-server-1"}
        )
        self.assertIn("Create metric widget", result)
        self.assertIn("Title: CPU Usage", result)
        self.assertIn("Metric: cpu.usage", result)
        self.assertIn("Time range: last 24 hours", result)
        self.assertIn("Aggregation: avg", result)
        self.assertIn("Filters:", result)

    def test_create_chart_widget_prompt_content(self):
        """Test that create_chart_widget returns expected prompt content."""
        result = CustomDashboardPrompts.create_chart_widget(
            title="Performance Chart",
            chart_type="line",
            metrics=["cpu.usage", "memory.usage"],
            time_range="last 1 hour",
            group_by="host"
        )
        self.assertIn("Create chart widget", result)
        self.assertIn("Title: Performance Chart", result)
        self.assertIn("Chart type: line", result)
        self.assertIn("Metrics:", result)
        self.assertIn("Time range: last 1 hour", result)
        self.assertIn("Group by: host", result)

    def test_create_application_dashboard_prompt_content(self):
        """Test that create_application_dashboard returns expected prompt content."""
        result = CustomDashboardPrompts.create_application_dashboard(
            application_name="MyApp",
            include_metrics=["response_time", "error_rate"],
            include_topology=True,
            time_range="last 6 hours"
        )
        self.assertIn("Create application dashboard", result)
        self.assertIn("Application: MyApp", result)
        self.assertIn("Metrics:", result)
        self.assertIn("Include topology: True", result)
        self.assertIn("Time range: last 6 hours", result)

    def test_create_dashboard_with_minimal_params(self):
        """Test create_dashboard with only required parameters."""
        result = CustomDashboardPrompts.create_dashboard(title="Minimal Dashboard")
        self.assertIn("Create a new custom dashboard", result)
        self.assertIn("Title: Minimal Dashboard", result)
        self.assertIn("Description: None", result)
        self.assertIn("Widgets: None", result)

    def test_get_dashboard_list_with_no_filters(self):
        """Test get_dashboard_list with no filters."""
        result = CustomDashboardPrompts.get_dashboard_list()
        self.assertIn("Get custom dashboards list", result)
        self.assertIn("Limit: None", result)
        self.assertIn("Tags filter: None", result)
        self.assertIn("Search: None", result)

    def test_update_dashboard_with_partial_updates(self):
        """Test update_dashboard with only some fields."""
        result = CustomDashboardPrompts.update_dashboard(
            dashboard_id="dashboard-123",
            title="New Title"
        )
        self.assertIn("Update custom dashboard", result)
        self.assertIn("Dashboard ID: dashboard-123", result)
        self.assertIn("Title: New Title", result)
        self.assertIn("Description: None", result)

    def test_create_metric_widget_with_defaults(self):
        """Test create_metric_widget with default values."""
        result = CustomDashboardPrompts.create_metric_widget(
            title="Simple Metric",
            metric_name="requests.count"
        )
        self.assertIn("Create metric widget", result)
        self.assertIn("Title: Simple Metric", result)
        self.assertIn("Metric: requests.count", result)
        self.assertIn("Time range: last 1 hour", result)
        self.assertIn("Aggregation: None", result)

    def test_create_chart_widget_with_minimal_params(self):
        """Test create_chart_widget with minimal parameters."""
        result = CustomDashboardPrompts.create_chart_widget(
            title="Basic Chart",
            chart_type="bar",
            metrics=["metric1"]
        )
        self.assertIn("Create chart widget", result)
        self.assertIn("Title: Basic Chart", result)
        self.assertIn("Chart type: bar", result)
        self.assertIn("Time range: last 1 hour", result)
        self.assertIn("Group by: None", result)

    def test_create_application_dashboard_with_defaults(self):
        """Test create_application_dashboard with default values."""
        result = CustomDashboardPrompts.create_application_dashboard(
            application_name="TestApp"
        )
        self.assertIn("Create application dashboard", result)
        self.assertIn("Application: TestApp", result)
        self.assertIn("Metrics: None", result)
        self.assertIn("Include topology: None", result)
        self.assertIn("Time range: last 1 hour", result)


    def test_create_dashboard_with_empty_lists(self):
        """Test create_dashboard with empty lists"""
        result = CustomDashboardPrompts.create_dashboard(
            title="Test",
            widgets=[],
            access_rules=[],
            tags=[]
        )
        self.assertIn("Widgets: None", result)
        self.assertIn("Access rules: None", result)
        self.assertIn("Tags: None", result)

    def test_get_dashboard_list_with_zero_limit(self):
        """Test get_dashboard_list with limit=0"""
        result = CustomDashboardPrompts.get_dashboard_list(limit=0)
        # 0 is falsy, so it becomes None
        self.assertIn("Limit: None", result)

    def test_get_dashboard_list_with_empty_search(self):
        """Test get_dashboard_list with empty search string"""
        result = CustomDashboardPrompts.get_dashboard_list(search="")
        # Empty string is falsy
        self.assertIn("Search: None", result)

    def test_update_dashboard_with_empty_title(self):
        """Test update_dashboard with empty title"""
        result = CustomDashboardPrompts.update_dashboard(
            dashboard_id="dash-1",
            title=""
        )
        # Empty string is falsy
        self.assertIn("Title: None", result)

    def test_create_metric_widget_with_empty_filters(self):
        """Test create_metric_widget with empty filters dict"""
        result = CustomDashboardPrompts.create_metric_widget(
            title="Test",
            metric_name="test.metric",
            filters={}
        )
        self.assertIn("Filters: None", result)

    def test_create_chart_widget_with_empty_metrics_list(self):
        """Test create_chart_widget with empty metrics list"""
        result = CustomDashboardPrompts.create_chart_widget(
            title="Test",
            chart_type="line",
            metrics=[]
        )
        self.assertIn("Metrics: []", result)

    def test_create_application_dashboard_with_empty_metrics(self):
        """Test create_application_dashboard with empty metrics list"""
        result = CustomDashboardPrompts.create_application_dashboard(
            application_name="App",
            include_metrics=[]
        )
        self.assertIn("Metrics: None", result)

    def test_create_application_dashboard_with_false_topology(self):
        """Test create_application_dashboard with include_topology=False"""
        result = CustomDashboardPrompts.create_application_dashboard(
            application_name="App",
            include_topology=False
        )
        # False is falsy
        self.assertIn("Include topology: None", result)

    def test_get_dashboard_details_with_special_chars(self):
        """Test get_dashboard_details with special characters in ID"""
        result = CustomDashboardPrompts.get_dashboard_details(
            dashboard_id="dash-123_test.v2"
        )
        self.assertIn("Dashboard ID: dash-123_test.v2", result)

    def test_get_shareable_users_with_special_chars(self):
        """Test get_shareable_users with special characters in ID"""
        result = CustomDashboardPrompts.get_shareable_users(
            dashboard_id="dash-123_test.v2"
        )
        self.assertIn("Dashboard ID: dash-123_test.v2", result)

    def test_get_shareable_api_tokens_with_special_chars(self):
        """Test get_shareable_api_tokens with special characters in ID"""
        result = CustomDashboardPrompts.get_shareable_api_tokens(
            dashboard_id="dash-123_test.v2"
        )
        self.assertIn("Dashboard ID: dash-123_test.v2", result)

    def test_all_prompts_return_strings(self):
        """Test that all prompt methods return strings"""
        prompts = CustomDashboardPrompts.get_prompts()
        for name, prompt_func in prompts:
            # Call with minimal required params
            if name == "create_dashboard":
                result = prompt_func(title="Test")
            elif name == "get_dashboard_list":
                result = prompt_func()
            elif name in {"get_dashboard_details", "update_dashboard", "delete_dashboard", "get_shareable_users", "get_shareable_api_tokens"}:
                result = prompt_func(dashboard_id="test")
            elif name == "create_metric_widget":
                result = prompt_func(title="Test", metric_name="test.metric")
            elif name == "create_chart_widget":
                result = prompt_func(title="Test", chart_type="line", metrics=["m1"])
            elif name == "create_application_dashboard":
                result = prompt_func(application_name="App")

            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_get_prompts_returns_tuples(self):
        """Test that get_prompts returns list of tuples"""
        prompts = CustomDashboardPrompts.get_prompts()
        for item in prompts:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            self.assertIsInstance(item[0], str)
            self.assertTrue(callable(item[1]))

    def test_prompt_names_are_unique(self):
        """Test that all prompt names are unique"""
        prompts = CustomDashboardPrompts.get_prompts()
        names = [p[0] for p in prompts]
        self.assertEqual(len(names), len(set(names)))

    def test_class_is_instantiable(self):
        """Test that the class can be instantiated"""
        instance = CustomDashboardPrompts()
        self.assertIsInstance(instance, CustomDashboardPrompts)

    def test_prompts_accessible_from_instance(self):
        """Test that prompts are accessible from instance"""
        instance = CustomDashboardPrompts()
        self.assertTrue(hasattr(instance, 'create_dashboard'))
        self.assertTrue(hasattr(instance, 'get_dashboard_list'))


if __name__ == '__main__':
    unittest.main()

