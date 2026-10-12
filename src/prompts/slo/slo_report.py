from typing import Optional

from src.prompts import auto_register_prompt


class SLOReportPrompts:
    """Class containing SLO report related prompts"""

    @auto_register_prompt
    @staticmethod
    def get_slo_report(
        slo_id: str,
        var_from: Optional[str] = None,
        to: Optional[str] = None,
        exclude_correction_id: Optional[list] = None,
        include_correction_id: Optional[list] = None,
    ) -> str:
        """Generate a Service Level Objective report for a specific SLO configuration"""
        return f"""
        Get SLO report:
        - SLO ID: {slo_id}
        - From: {var_from or '1 hour ago'}
        - To: {to or 'now'}
        - Exclude correction IDs: {exclude_correction_id or 'None'}
        - Include correction IDs: {include_correction_id or 'None'}
        """

    @classmethod
    def get_prompts(cls):
        """Return all prompts defined in this class"""
        return [
            ('get_slo_report', cls.get_slo_report),
        ]
