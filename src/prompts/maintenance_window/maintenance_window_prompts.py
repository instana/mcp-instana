"""
Maintenance Window Prompts for WatsonX Assistant Integration

These prompts help WatsonX Assistant understand how to map natural language
requests to the maintenance window management tool parameters.
"""

from typing import Optional

from src.prompts import auto_register_prompt


class MaintenanceWindowPrompts:
    """Class containing maintenance window related prompts"""

    @auto_register_prompt
    @staticmethod
    def create_maintenance_window(
        imap_code: str,
        start_time: str,
        duration_minutes: Optional[str] = None,
        duration_hours: Optional[str] = None,
        template: Optional[str] = None,
        reason: Optional[str] = None
    ) -> str:
        """
        Create a new maintenance window in Instana for an application or IMAP code.

        Use this when the user says things like:
        - "Create a maintenance window for EAL-012471"
        - "Schedule maintenance for my application"
        - "Set up a maintenance window starting in 2 hours"
        - "Create a deployment maintenance window"
        - "Open a maintenance window for the next 2 hours"
        - "Schedule downtime for application EAL-012471"

        The start_time can be in natural language like "in 2 hours" or "tomorrow at 10am".
        """
        return f"""
Create a maintenance window:
- IMAP Code: {imap_code}
- Start Time: {start_time}
- Duration (minutes): {duration_minutes or '(use template default)'}
- Duration (hours): {duration_hours or '(not specified)'}
- Template: {template or '(not specified)'}
- Reason: {reason or '(not specified)'}

IMPORTANT: Call the manage_maintenance_windows tool with:
{{
  "resource_type": "window",
  "operation": "create",
  "imap_code": "{imap_code}",
  "start_time": "{start_time}",
  "duration_minutes": "{duration_minutes or ''}",
  "duration_hours": "{duration_hours or ''}",
  "template": "{template or ''}",
  "reason": "{reason or ''}"
}}
"""

    @auto_register_prompt
    @staticmethod
    def list_active_maintenance_windows(
        imap_code: Optional[str] = None
    ) -> str:
        """
        List all currently active maintenance windows in Instana.

        Use this when the user says things like:
        - "Show me active maintenance windows"
        - "What maintenance windows are currently running?"
        - "List active maintenance windows"
        - "Are there any maintenance windows active right now?"
        - "Which applications are in maintenance mode?"
        - "Show ongoing maintenance windows"
        """
        return f"""
List active maintenance windows:
- IMAP Code filter: {imap_code or '(all applications — no filter needed)'}

IMPORTANT: Call the manage_maintenance_windows tool IMMEDIATELY with:
{{
  "resource_type": "window",
  "operation": "list_active"{f', "imap_code": "{imap_code}"' if imap_code else ''}
}}

NOTE: imap_code is OPTIONAL. Do NOT ask the user for it. Call the tool immediately without imap_code to list all active windows.
"""

    @auto_register_prompt
    @staticmethod
    def list_all_maintenance_windows(
        imap_code: Optional[str] = None
    ) -> str:
        """
        List all maintenance windows in Instana including active, scheduled, and expired ones.

        Use this when the user says things like:
        - "Show me all maintenance windows"
        - "List all maintenance windows"
        - "Give me a full list of maintenance windows"
        - "Show maintenance window history"
        - "What maintenance windows exist?"
        - "Show all maintenance windows including past ones"
        """
        return f"""
List all maintenance windows (active, scheduled, and expired):
- IMAP Code filter: {imap_code or '(all applications — no filter needed)'}

IMPORTANT: Call the manage_maintenance_windows tool IMMEDIATELY with:
{{
  "resource_type": "window",
  "operation": "list_all"{f', "imap_code": "{imap_code}"' if imap_code else ''}
}}

NOTE: imap_code is OPTIONAL. Do NOT ask the user for it. Call the tool immediately without imap_code to list all windows.
"""

    @auto_register_prompt
    @staticmethod
    def list_scheduled_maintenance_windows(
        imap_code: Optional[str] = None
    ) -> str:
        """
        List all scheduled (upcoming/future) maintenance windows in Instana.

        Use this when the user says things like:
        - "Show me scheduled maintenance windows"
        - "What maintenance windows are scheduled?"
        - "List upcoming maintenance windows"
        - "Show future maintenance windows"
        - "What maintenance is planned?"
        - "Are there any scheduled maintenance windows for my applications?"
        - "Show me planned maintenance windows"
        - "Can you give me scheduled maintenance windows applications?"
        """
        return f"""
List scheduled (upcoming) maintenance windows:
- IMAP Code filter: {imap_code or '(all applications — no filter needed)'}

IMPORTANT: Call the manage_maintenance_windows tool IMMEDIATELY with:
{{
  "resource_type": "window",
  "operation": "list_scheduled"{f', "imap_code": "{imap_code}"' if imap_code else ''}
}}

NOTE: imap_code is OPTIONAL. Do NOT ask the user for it. Call the tool immediately without imap_code to list all scheduled windows across all applications.
"""

    @auto_register_prompt
    @staticmethod
    def modify_maintenance_window(
        window_id: str,
        duration_minutes: Optional[str] = None,
        end_time: Optional[str] = None,
        reason: Optional[str] = None
    ) -> str:
        """
        Modify or update an existing maintenance window in Instana.

        Use this when the user says things like:
        - "Extend maintenance window mw-789 by 30 minutes"
        - "Update the maintenance window duration"
        - "Change the end time of maintenance window"
        - "Modify maintenance window mw-789"
        - "Extend the current maintenance window"
        - "Update the reason for maintenance window"
        """
        return f"""
Modify maintenance window:
- Window ID: {window_id}
- New Duration (minutes): {duration_minutes or '(not changing)'}
- New End Time: {end_time or '(not changing)'}
- New Reason: {reason or '(not changing)'}

IMPORTANT: Call the manage_maintenance_windows tool with:
{{
  "resource_type": "window",
  "operation": "modify",
  "window_id": "{window_id}",
  "duration_minutes": "{duration_minutes or ''}",
  "end_time": "{end_time or ''}",
  "reason": "{reason or ''}"
}}
"""

    @auto_register_prompt
    @staticmethod
    def close_maintenance_window(
        window_id: str,
        completion_notes: Optional[str] = None
    ) -> str:
        """
        Close or end an active maintenance window in Instana.

        Use this when the user says things like:
        - "Close maintenance window mw-789"
        - "End the maintenance window"
        - "Complete maintenance window mw-789"
        - "Mark maintenance window as done"
        - "Finish the maintenance window"
        - "Close the maintenance window with notes"
        """
        return f"""
Close maintenance window:
- Window ID: {window_id}
- Completion Notes: {completion_notes or '(not specified)'}

IMPORTANT: Call the manage_maintenance_windows tool with:
{{
  "resource_type": "window",
  "operation": "close",
  "window_id": "{window_id}",
  "completion_notes": "{completion_notes or ''}"
}}
"""

    @auto_register_prompt
    @staticmethod
    def get_maintenance_templates() -> str:
        """
        Get all available maintenance window templates in Instana.

        Use this when the user says things like:
        - "What maintenance window templates are available?"
        - "Show me maintenance templates"
        - "List maintenance window types"
        - "What templates can I use for maintenance windows?"
        - "Show available maintenance window templates"
        - "What are the predefined maintenance window options?"
        """
        return """
Get maintenance window templates.

IMPORTANT: Call the manage_maintenance_windows tool with:
{
  "resource_type": "templates",
  "operation": "get"
}
"""

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('create_maintenance_window', cls.create_maintenance_window),
            ('list_active_maintenance_windows', cls.list_active_maintenance_windows),
            ('list_all_maintenance_windows', cls.list_all_maintenance_windows),
            ('list_scheduled_maintenance_windows', cls.list_scheduled_maintenance_windows),
            ('modify_maintenance_window', cls.modify_maintenance_window),
            ('close_maintenance_window', cls.close_maintenance_window),
            ('get_maintenance_templates', cls.get_maintenance_templates),
        ]
