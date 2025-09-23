from typing import Any, Dict, List, Optional

from src.prompts import auto_register_prompt


class CustomDashboardPrompts:
    """Class containing custom dashboard related prompts"""

    @auto_register_prompt
    @staticmethod
    def create_dashboard(title: str,
                        widgets: Optional[List[Dict[str, Any]]] = None,
                        access_rules: Optional[List[Dict[str, Any]]] = None,
                        description: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> str:
        """Create a new custom dashboard with specified configuration"""
        return f"""
        Create a new custom dashboard with:
        - Title: {title}
        - Description: {description or 'None'}
        - Widgets: {widgets or 'None'}
        - Access rules: {access_rules or 'None'}
        - Tags: {tags or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_dashboard_list(limit: Optional[int] = None,
                          tags: Optional[List[str]] = None,
                          search: Optional[str] = None) -> str:
        """Retrieve a list of all custom dashboards"""
        return f"""
        Get custom dashboards list:
        - Limit: {limit or 'None'}
        - Tags filter: {tags or 'None'}
        - Search: {search or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def get_dashboard_details(dashboard_id: str) -> str:
        """Get detailed information about a specific custom dashboard"""
        return f"""
        Get custom dashboard details:
        - Dashboard ID: {dashboard_id}
        """

    @auto_register_prompt
    @staticmethod
    def update_dashboard(dashboard_id: str,
                        title: Optional[str] = None,
                        widgets: Optional[List[Dict[str, Any]]] = None,
                        access_rules: Optional[List[Dict[str, Any]]] = None,
                        description: Optional[str] = None,
                        tags: Optional[List[str]] = None) -> str:
        """Update an existing custom dashboard configuration"""
        return f"""
        Update custom dashboard:
        - Dashboard ID: {dashboard_id}
        - Title: {title or 'None'}
        - Description: {description or 'None'}
        - Widgets: {widgets or 'None'}
        - Access rules: {access_rules or 'None'}
        - Tags: {tags or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def delete_dashboard(dashboard_id: str) -> str:
        """Delete a custom dashboard"""
        return f"""
        Delete custom dashboard:
        - Dashboard ID: {dashboard_id}
        """

    @auto_register_prompt
    @staticmethod
    def get_shareable_users(dashboard_id: str) -> str:
        """Get list of users who can be granted access to a custom dashboard"""
        return f"""
        Get shareable users for dashboard:
        - Dashboard ID: {dashboard_id}
        """

    @auto_register_prompt
    @staticmethod
    def get_shareable_api_tokens(dashboard_id: str) -> str:
        """Get list of API tokens that can access a custom dashboard"""
        return f"""
        Get shareable API tokens for dashboard:
        - Dashboard ID: {dashboard_id}
        """

    @auto_register_prompt
    @staticmethod
    def create_metric_widget(title: str,
                           metric_name: str,
                           time_range: Optional[str] = None,
                           aggregation: Optional[str] = None,
                           filters: Optional[Dict[str, Any]] = None) -> str:
        """Create a metric widget for a custom dashboard"""
        return f"""
        Create metric widget:
        - Title: {title}
        - Metric: {metric_name}
        - Time range: {time_range or 'last 1 hour'}
        - Aggregation: {aggregation or 'None'}
        - Filters: {filters or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def create_chart_widget(title: str,
                          chart_type: str,
                          metrics: List[str],
                          time_range: Optional[str] = None,
                          group_by: Optional[str] = None) -> str:
        """Create a chart widget for a custom dashboard"""
        return f"""
        Create chart widget:
        - Title: {title}
        - Chart type: {chart_type}
        - Metrics: {metrics}
        - Time range: {time_range or 'last 1 hour'}
        - Group by: {group_by or 'None'}
        """

    @auto_register_prompt
    @staticmethod
    def create_application_dashboard(application_name: str,
                                   include_metrics: Optional[List[str]] = None,
                                   include_topology: Optional[bool] = None,
                                   time_range: Optional[str] = None) -> str:
        """Create a comprehensive dashboard for a specific application"""
        return f"""
        Create application dashboard:
        - Application: {application_name}
        - Metrics: {include_metrics or 'None'}
        - Include topology: {include_topology or 'None'}
        - Time range: {time_range or 'last 1 hour'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('create_dashboard', cls.create_dashboard),
            ('get_dashboard_list', cls.get_dashboard_list),
            ('get_dashboard_details', cls.get_dashboard_details),
            ('update_dashboard', cls.update_dashboard),
            ('delete_dashboard', cls.delete_dashboard),
            ('get_shareable_users', cls.get_shareable_users),
            ('get_shareable_api_tokens', cls.get_shareable_api_tokens),
            ('create_metric_widget', cls.create_metric_widget),
            ('create_chart_widget', cls.create_chart_widget),
            ('create_application_dashboard', cls.create_application_dashboard),
        ]
