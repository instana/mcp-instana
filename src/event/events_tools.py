"""
Agent Monitoring Events MCP Tools Module

This module provides agent monitoring events-specific MCP tools for Instana monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

# Import the correct class name (EventsApi with lowercase 'i')
from instana_client.api.events_api import EventsApi

from src.core.utils import BaseInstanaClient, register_as_tool, with_header_auth

# Configure logger for this module
logger = logging.getLogger(__name__)

class AgentMonitoringEventsMCPTools(BaseInstanaClient):
    """Tools for agent monitoring events in Instana MCP."""

    def __init__(self, read_token: str, base_url: str):
        """Initialize the Agent Monitoring Events MCP tools client."""
        super().__init__(read_token=read_token, base_url=base_url)

    @register_as_tool
    @with_header_auth(EventsApi)
    async def get_event(self, event_id: str, ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get a specific event by ID.

        Args:
            event_id: The ID of the event to retrieve
            ctx: The MCP context (optional)
            api_client: API client for testing (optional)

        Returns:
            Dictionary containing the event data or error information
        """
        try:
            # Call the get_event method from the SDK
            result = api_client.get_event(event_id=event_id)

            return result
        except Exception as e:
            logger.error(f"Error in get_event: {e}", exc_info=True)
            return {"error": f"Failed to get event: {e!s}"}

    @register_as_tool
    @with_header_auth(EventsApi)
    async def get_kubernetes_info_events(self,
                                         from_time: Optional[int] = None,
                                         to_time: Optional[int] = None,
                                         time_range: Optional[str] = None,
                                         max_events: Optional[int] = 50,  # Added parameter to limit events
                                         ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get Kubernetes info events based on the provided parameters and return a detailed analysis.

        This tool retrieves Kubernetes events from Instana and provides a detailed analysis focusing on top problems,
        their details, and actionable fix suggestions. You can specify a time range using timestamps or natural language
        like "last 24 hours" or "last 2 days".

        Args:
            from_time: Start timestamp in milliseconds since epoch (optional)
            to_time: End timestamp in milliseconds since epoch (optional)
            time_range: Natural language time range like "last 24 hours", "last 2 days", "last week" (optional)
            max_events: Maximum number of events to process (default: 50)
            ctx: The MCP context (optional)
            api_client: API client for testing (optional)

        Returns:
            Dictionary containing detailed Kubernetes events analysis or error information
        """
        try:
            # Process natural language time range if provided
            if time_range:
                logger.debug(f"Processing natural language time range: '{time_range}'")

                # Current time in milliseconds
                current_time_ms = int(datetime.now().timestamp() * 1000)

                # Default to 24 hours if just "last few hours" is specified
                if time_range.lower() in ["last few hours", "last hours", "few hours"]:
                    hours = 24
                    from_time = current_time_ms - (hours * 60 * 60 * 1000)
                    to_time = current_time_ms
                    logger.debug(f"Interpreted as last {hours} hours")
                # Extract hours if specified
                elif "hour" in time_range.lower():
                    import re
                    hour_match = re.search(r'(\d+)\s*hour', time_range.lower())
                    hours = int(hour_match.group(1)) if hour_match else 24
                    from_time = current_time_ms - (hours * 60 * 60 * 1000)
                    to_time = current_time_ms
                # Extract days if specified
                elif "day" in time_range.lower():
                    import re
                    day_match = re.search(r'(\d+)\s*day', time_range.lower())
                    days = int(day_match.group(1)) if day_match else 1
                    from_time = current_time_ms - (days * 24 * 60 * 60 * 1000)
                    to_time = current_time_ms
                # Handle "last week"
                elif "week" in time_range.lower():
                    import re
                    week_match = re.search(r'(\d+)\s*week', time_range.lower())
                    weeks = int(week_match.group(1)) if week_match else 1
                    from_time = current_time_ms - (weeks * 7 * 24 * 60 * 60 * 1000)
                    to_time = current_time_ms
                # Handle "last month"
                elif "month" in time_range.lower():
                    import re
                    month_match = re.search(r'(\d+)\s*month', time_range.lower())
                    months = int(month_match.group(1)) if month_match else 1
                    from_time = current_time_ms - (months * 30 * 24 * 60 * 60 * 1000)
                    to_time = current_time_ms
                # Default to 24 hours for any other time range
                else:
                    hours = 24
                    from_time = current_time_ms - (hours * 60 * 60 * 1000)
                    to_time = current_time_ms

            # Set default time range if not provided
            if not to_time:
                to_time = int(datetime.now().timestamp() * 1000)
            if not from_time:
                from_time = to_time - (24 * 60 * 60 * 1000)  # Default to 24 hours

            # Call the kubernetes_info_events method from the SDK
            result = api_client.kubernetes_info_events(
                to=to_time,
                var_from=from_time,
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

            # Print the raw result for debugging
            logger.debug(f"Raw API result type: {type(result)}")
            logger.debug(f"Raw API result length: {len(result) if isinstance(result, list) else 'not a list'}")

            # If there are no events, return early
            if not result or (isinstance(result, list) and len(result) == 0):
                from_date = datetime.fromtimestamp(from_time/1000).strftime('%Y-%m-%d %H:%M:%S')
                to_date = datetime.fromtimestamp(to_time/1000).strftime('%Y-%m-%d %H:%M:%S')
                return {
                    "analysis": f"No Kubernetes events found between {from_date} and {to_date}.",
                    "time_range": f"{from_date} to {to_date}",
                    "events_count": 0
                }

            # Process the events to create a summary
            events = result if isinstance(result, list) else [result]

            # Get the total number of events before limiting
            total_events_count = len(events)

            # Limit the number of events to process
            events = events[:max_events]
            logger.debug(f"Limited to processing {len(events)} events out of {total_events_count} total events")

            # Convert InfraEventResult objects to dictionaries if needed
            event_dicts = []
            for event in events:
                if hasattr(event, 'to_dict'):
                    event_dicts.append(event.to_dict())
                else:
                    event_dicts.append(event)

            # Group events by problem type
            problem_groups = {}

            # Process each event
            for event in event_dicts:
                problem = event.get("problem", "Unknown")

                # Initialize problem group if not exists
                if problem not in problem_groups:
                    problem_groups[problem] = {
                        "count": 0,
                        "affected_namespaces": set(),
                        "affected_entities": set(),
                        "details": set(),
                        "fix_suggestions": set(),
                        "sample_events": []
                    }

                # Update problem group
                problem_groups[problem]["count"] += 1

                # Extract namespace from entityLabel
                entity_label = event.get("entityLabel", "")
                if "/" in entity_label:
                    namespace, entity = entity_label.split("/", 1)
                    problem_groups[problem]["affected_namespaces"].add(namespace)
                    problem_groups[problem]["affected_entities"].add(entity)

                # Add detail and fix suggestion
                detail = event.get("detail", "")
                if detail:
                    problem_groups[problem]["details"].add(detail)

                fix_suggestion = event.get("fixSuggestion", "")
                if fix_suggestion:
                    problem_groups[problem]["fix_suggestions"].add(fix_suggestion)

                # Add sample event (up to 3 per problem)
                if len(problem_groups[problem]["sample_events"]) < 3:
                    simple_event = {
                        "eventId": event.get("eventId", ""),
                        "start": event.get("start", 0),
                        "entityLabel": event.get("entityLabel", ""),
                        "detail": detail
                    }
                    problem_groups[problem]["sample_events"].append(simple_event)

            # Sort problems by count (most frequent first)
            sorted_problems = sorted(problem_groups.items(), key=lambda x: x[1]["count"], reverse=True)

            # Format the time range in a human-readable format
            from_date = datetime.fromtimestamp(from_time/1000).strftime('%Y-%m-%d %H:%M:%S')
            to_date = datetime.fromtimestamp(to_time/1000).strftime('%Y-%m-%d %H:%M:%S')

            # Create a detailed analysis of each problem
            problem_analyses = []

            # Process each problem
            for problem_name, problem_data in sorted_problems:
                # Create a detailed problem analysis
                problem_analysis = {
                    "problem": problem_name,
                    "count": problem_data["count"],
                    "affected_namespaces": list(problem_data["affected_namespaces"]),
                    "details": list(problem_data["details"]),
                    "fix_suggestions": list(problem_data["fix_suggestions"]),
                    "sample_events": problem_data["sample_events"]
                }

                problem_analyses.append(problem_analysis)

            # Create a comprehensive analysis
            analysis_result = {
                "summary": f"Analysis based on {len(events)} of {total_events_count} Kubernetes events between {from_date} and {to_date}.",
                "time_range": f"{from_date} to {to_date}",
                "events_count": total_events_count,
                "events_analyzed": len(events),
                "problem_analyses": problem_analyses[:10]  # Limit to top 10 problems for readability
            }

            # Create a more user-friendly text summary for direct display
            markdown_summary = "# Kubernetes Events Analysis\n\n"
            markdown_summary += f"Analysis based on {len(events)} of {total_events_count} Kubernetes events between {from_date} and {to_date}.\n\n"

            markdown_summary += "## Top Problems\n\n"

            # Add each problem to the markdown summary
            for problem_analysis in problem_analyses[:5]:  # Limit to top 5 for readability
                problem_name = problem_analysis["problem"]
                count = problem_analysis["count"]

                markdown_summary += f"### {problem_name} ({count} events)\n\n"

                # Add affected namespaces if available
                if problem_analysis.get("affected_namespaces"):
                    namespaces = ", ".join(problem_analysis["affected_namespaces"][:5])
                    if len(problem_analysis["affected_namespaces"]) > 5:
                        namespaces += f" and {len(problem_analysis['affected_namespaces']) - 5} more"
                    markdown_summary += f"**Affected Namespaces:** {namespaces}\n\n"

                # Add fix suggestions
                if problem_analysis.get("fix_suggestions"):
                    markdown_summary += "**Fix Suggestions:**\n\n"
                    for suggestion in list(problem_analysis["fix_suggestions"])[:3]:  # Limit to top 3 suggestions
                        markdown_summary += f"- {suggestion}\n"

                markdown_summary += "\n"

            # Add the markdown summary to the result
            analysis_result["markdown_summary"] = markdown_summary

            return analysis_result

        except Exception as e:
            logger.error(f"Error in get_kubernetes_info_events: {e}", exc_info=True)
            return {
                "error": f"Failed to get Kubernetes info events: {e!s}"
            }

    @register_as_tool
    @with_header_auth(EventsApi)
    async def get_agent_monitoring_events(self,
                                          query: Optional[str] = None,
                                          from_time: Optional[int] = None,
                                          to_time: Optional[int] = None,
                                          size: Optional[int] = 100,
                                          max_events: Optional[int] = 50,  # Added parameter to limit events
                                          time_range: Optional[str] = None,  # Added parameter for natural language time range
                                          ctx=None, api_client=None) -> Dict[str, Any]:
        """
        Get agent monitoring events from Instana and return a detailed analysis.

        This tool retrieves agent monitoring events from Instana and provides a detailed analysis focusing on
        monitoring issues, their frequency, and affected entities. You can specify a time range using timestamps
        or natural language like "last 24 hours" or "last 2 days".

        Args:
            query: Query string to filter events (optional)
            from_time: Start timestamp in milliseconds since epoch (optional, defaults to 1 hour ago)
            to_time: End timestamp in milliseconds since epoch (optional, defaults to now)
            size: Maximum number of events to return from API (optional, default 100)
            max_events: Maximum number of events to process for analysis (optional, default 50)
            time_range: Natural language time range like "last 24 hours", "last 2 days", "last week" (optional)
            ctx: The MCP context (optional)
            api_client: API client for testing (optional)

        Returns:
            Dictionary containing summarized agent monitoring events data or error information
        """
        try:
            # Process natural language time range if provided
            if time_range:
                logger.debug(f"Processing natural language time range: '{time_range}'")

                # Current time in milliseconds
                current_time_ms = int(datetime.now().timestamp() * 1000)

                # Default to 24 hours if just "last few hours" is specified
                if time_range.lower() in ["last few hours", "last hours", "few hours"]:
                    hours = 24
                    from_time = current_time_ms - (hours * 60 * 60 * 1000)
                    to_time = current_time_ms
                    logger.debug(f"Interpreted as last {hours} hours")
                # Extract hours if specified
                elif "hour" in time_range.lower():
                    import re
                    hour_match = re.search(r'(\d+)\s*hour', time_range.lower())
                    hours = int(hour_match.group(1)) if hour_match else 24
                    from_time = current_time_ms - (hours * 60 * 60 * 1000)
                    to_time = current_time_ms
                # Extract days if specified
                elif "day" in time_range.lower():
                    import re
                    day_match = re.search(r'(\d+)\s*day', time_range.lower())
                    days = int(day_match.group(1)) if day_match else 1
                    from_time = current_time_ms - (days * 24 * 60 * 60 * 1000)
                    to_time = current_time_ms
                # Handle "last week"
                elif "week" in time_range.lower():
                    import re
                    week_match = re.search(r'(\d+)\s*week', time_range.lower())
                    weeks = int(week_match.group(1)) if week_match else 1
                    from_time = current_time_ms - (weeks * 7 * 24 * 60 * 60 * 1000)
                    to_time = current_time_ms
                # Handle "last month"
                elif "month" in time_range.lower():
                    import re
                    month_match = re.search(r'(\d+)\s*month', time_range.lower())
                    months = int(month_match.group(1)) if month_match else 1
                    from_time = current_time_ms - (months * 30 * 24 * 60 * 60 * 1000)
                    to_time = current_time_ms
                # Default to 24 hours for any other time range
                else:
                    hours = 24
                    from_time = current_time_ms - (hours * 60 * 60 * 1000)
                    to_time = current_time_ms

            logger.debug(f"get_agent_monitoring_events called with query={query}, from_time={from_time}, to_time={to_time}, size={size}")

            # Set default time range if not provided
            if not to_time:
                to_time = int(datetime.now().timestamp() * 1000)

            if not from_time:
                from_time = to_time - (60 * 60 * 1000)  # Default to 1 hour

            # Call the agent_monitoring_events method from the SDK
            result = api_client.agent_monitoring_events(
                to=to_time,
                var_from=from_time,
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

            # Print the raw result for debugging
            logger.debug(f"Raw API result type: {type(result)}")
            logger.debug(f"Raw API result length: {len(result) if isinstance(result, list) else 'not a list'}")

            # If there are no events, return early
            if not result or (isinstance(result, list) and len(result) == 0):
                from_date = datetime.fromtimestamp(from_time/1000).strftime('%Y-%m-%d %H:%M:%S')
                to_date = datetime.fromtimestamp(to_time/1000).strftime('%Y-%m-%d %H:%M:%S')
                return {
                    "analysis": f"No agent monitoring events found between {from_date} and {to_date}.",
                    "time_range": f"{from_date} to {to_date}",
                    "events_count": 0
                }

            # Process the events to create a summary
            events = result if isinstance(result, list) else [result]

            # Get the total number of events before limiting
            total_events_count = len(events)

            # Limit the number of events to process
            events = events[:max_events]
            logger.debug(f"Limited to processing {len(events)} events out of {total_events_count} total events")

            # Convert objects to dictionaries if needed
            event_dicts = []
            for event in events:
                if hasattr(event, 'to_dict'):
                    event_dicts.append(event.to_dict())
                else:
                    event_dicts.append(event)

            # Group events by problem type
            problem_groups = {}

            # Process each event
            for event in event_dicts:
                # Extract the monitoring issue from the problem field
                full_problem = event.get("problem", "Unknown")
                # Strip "Monitoring issue: " prefix if present
                problem = full_problem.replace("Monitoring issue: ", "") if "Monitoring issue: " in full_problem else full_problem

                # Initialize problem group if not exists
                if problem not in problem_groups:
                    problem_groups[problem] = {
                        "count": 0,
                        "affected_entities": set(),
                        "entity_types": set(),
                        "sample_events": []
                    }

                # Update problem group
                problem_groups[problem]["count"] += 1

                # Add entity information
                entity_name = event.get("entityName", "Unknown")
                entity_label = event.get("entityLabel", "Unknown")
                entity_type = event.get("entityType", "Unknown")

                entity_info = f"{entity_name} ({entity_label})"
                problem_groups[problem]["affected_entities"].add(entity_info)
                problem_groups[problem]["entity_types"].add(entity_type)

                # Add sample event (up to 3 per problem)
                if len(problem_groups[problem]["sample_events"]) < 3:
                    simple_event = {
                        "eventId": event.get("eventId", ""),
                        "start": event.get("start", 0),
                        "entityName": entity_name,
                        "entityLabel": entity_label,
                        "severity": event.get("severity", 0)
                    }
                    problem_groups[problem]["sample_events"].append(simple_event)

            # Sort problems by count (most frequent first)
            sorted_problems = sorted(problem_groups.items(), key=lambda x: x[1]["count"], reverse=True)

            # Format the time range in a human-readable format
            from_date = datetime.fromtimestamp(from_time/1000).strftime('%Y-%m-%d %H:%M:%S')
            to_date = datetime.fromtimestamp(to_time/1000).strftime('%Y-%m-%d %H:%M:%S')

            # Create a detailed analysis of each problem
            problem_analyses = []

            # Process each problem
            for problem_name, problem_data in sorted_problems:
                # Create a detailed problem analysis
                problem_analysis = {
                    "problem": problem_name,
                    "count": problem_data["count"],
                    "affected_entities": list(problem_data["affected_entities"]),
                    "entity_types": list(problem_data["entity_types"]),
                    "sample_events": problem_data["sample_events"]
                }

                problem_analyses.append(problem_analysis)

            # Create a comprehensive analysis
            analysis_result = {
                "summary": f"Analysis based on {len(events)} of {total_events_count} agent monitoring events between {from_date} and {to_date}.",
                "time_range": f"{from_date} to {to_date}",
                "events_count": total_events_count,
                "events_analyzed": len(events),
                "problem_analyses": problem_analyses[:10]  # Limit to top 10 problems for readability
            }

            # Create a more user-friendly text summary for direct display
            markdown_summary = "# Agent Monitoring Events Analysis\n\n"
            markdown_summary += f"Analysis based on {len(events)} of {total_events_count} agent monitoring events between {from_date} and {to_date}.\n\n"

            markdown_summary += "## Top Monitoring Issues\n\n"

            # Add each problem to the markdown summary
            for problem_analysis in problem_analyses[:5]:  # Limit to top 5 for readability
                problem_name = problem_analysis["problem"]
                count = problem_analysis["count"]

                markdown_summary += f"### {problem_name} ({count} events)\n\n"

                # Add affected entities if available
                if problem_analysis.get("affected_entities"):
                    entities = ", ".join(problem_analysis["affected_entities"][:5])
                    if len(problem_analysis["affected_entities"]) > 5:
                        entities += f" and {len(problem_analysis['affected_entities']) - 5} more"
                    markdown_summary += f"**Affected Entities:** {entities}\n\n"

                markdown_summary += "\n"

            # Add the markdown summary to the result
            analysis_result["markdown_summary"] = markdown_summary

            return analysis_result

        except Exception as e:
            logger.error(f"Error in get_agent_monitoring_events: {e}", exc_info=True)
            return {
                "error": f"Failed to get agent monitoring events: {e!s}"
            }

