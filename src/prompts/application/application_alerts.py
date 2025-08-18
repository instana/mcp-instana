from typing import Optional

from src.prompts import auto_register_prompt


class ApplicationAlertsPrompts:
    """Class containing application alerts related prompts"""


    @auto_register_prompt
    @staticmethod
    def app_alerts_list(from_time: Optional[int]=None, to_time: Optional[int]=None, name_filter: Optional[str] = None, severity: Optional[str] = None) -> str:
        """List all application alerts in Instana server"""
        return f"""
        List application alerts with filters:
        - Name filter: {name_filter or 'None'}
        - Severity: {severity or 'None'}
        - Time range: {from_time} to {to_time or 'current time'}
        """


    @auto_register_prompt
    @staticmethod
    def app_alert_details(alert_ids: Optional[list] = None, application_id: Optional[str] = None) -> str:
        """Get Smart Alert Configurations details for a specific application"""
        return f"""
        Get alert details for:
        - Alert IDs: {alert_ids or 'None'}
        - Application ID: {application_id or 'None'}
        """


    @auto_register_prompt
    @staticmethod
    def app_alert_config_delete(id: str) -> str:
        """Delete a Smart Alert Configuration by ID"""
        return f"Delete alert configuration with ID: {id}"


    @auto_register_prompt
    @staticmethod
    def app_alert_config_enable(id: str) -> str:
        """Enable a Smart Alert Configuration by ID"""
        return f"Enable alert configuration with ID: {id}"

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('app_alerts_list', cls.app_alerts_list),
            ('app_alert_details', cls.app_alert_details),
            ('app_alert_config_delete', cls.app_alert_config_delete),
            ('app_alert_config_enable', cls.app_alert_config_enable),
        ]
