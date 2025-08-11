"""
E2E tests for Agent Monitoring Events MCP Tools
"""

from unittest.mock import MagicMock, patch

import pytest


# Mock the ApiException since instana_client is not available in test environment
class ApiException(Exception):
    def __init__(self, status=None, reason=None, *args, **kwargs):
        self.status = status
        self.reason = reason
        super().__init__(*args, **kwargs)

from src.event.events_tools import AgentMonitoringEventsMCPTools


class TestAgentMonitoringEventsE2E:
    """End-to-end tests for Agent Monitoring Events MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        """Test initialization of the AgentMonitoringEventsMCPTools client."""

        # Create the client
        client = AgentMonitoringEventsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Verify the client was initialized correctly
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_event_success(self, instana_credentials):
        """Test getting an event by ID successfully."""

        # Mock the API response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "eventId": "event-123",
            "type": "kubernetes_info",
            "severity": 5,
            "start": 1625097600000,
            "end": 1625097900000,
            "entityId": "entity-123",
            "entityName": "test-entity",
            "entityLabel": "test-label",
            "problem": "Test Problem",
            "detail": "Test Detail"
        }

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.get_event.return_value = mock_response

        # Create the client
        client = AgentMonitoringEventsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method with the mock API client
        result = await client.get_event(event_id="event-123", api_client=mock_api_client)

        # Verify the API was called correctly
        mock_api_client.get_event.assert_called_once_with(event_id="event-123")

        # Verify the result - the method returns the API response directly
        assert result == mock_response

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_event_error(self, instana_credentials):
        """Test error handling when getting an event by ID."""

        # Create a mock API client that raises an exception
        mock_api_client = MagicMock()
        mock_api_client.get_event.side_effect = Exception("API Error")

        # Create the client
        client = AgentMonitoringEventsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_event(event_id="event-123", api_client=mock_api_client)

        # Verify the result contains an error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "API Error" in result["error"]

        # Verify the API was called
        mock_api_client.get_event.assert_called_once_with(event_id="event-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_event_api_exception(self, instana_credentials):
        """Test handling of ApiException when getting an event by ID."""

        # Create a mock API client that raises an ApiException
        mock_api_client = MagicMock()
        mock_api_client.get_event.side_effect = ApiException(status=404, reason="Not Found")

        # Create the client
        client = AgentMonitoringEventsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_event(event_id="event-123", api_client=mock_api_client)

        # Verify the result contains an error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get event" in result["error"]

        # Verify the API was called
        mock_api_client.get_event.assert_called_once_with(event_id="event-123")

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_kubernetes_info_events_success(self, instana_credentials):
        """Test getting Kubernetes info events successfully."""

        # Mock the API response
        mock_event1 = MagicMock()
        mock_event1.to_dict.return_value = {
            "eventId": "event-123",
            "type": "kubernetes_info",
            "severity": 5,
            "start": 1625097600000,
            "end": 1625097900000,
            "entityId": "entity-123",
            "entityName": "pod-1",
            "entityLabel": "namespace-1/pod-1",
            "problem": "Pod Restart",
            "detail": "Pod restarted due to OOM",
            "fixSuggestion": "Increase memory limits"
        }

        mock_event2 = MagicMock()
        mock_event2.to_dict.return_value = {
            "eventId": "event-456",
            "type": "kubernetes_info",
            "severity": 7,
            "start": 1625097700000,
            "end": 1625097800000,
            "entityId": "entity-456",
            "entityName": "pod-2",
            "entityLabel": "namespace-2/pod-2",
            "problem": "Pod Pending",
            "detail": "Pod pending due to insufficient resources",
            "fixSuggestion": "Scale up the cluster"
        }

        mock_response = [mock_event1, mock_event2]

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.kubernetes_info_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with from_time and to_time
            from_time = 1625097600000  # 2021-07-01 00:00:00 UTC
            to_time = 1625097900000    # 2021-07-01 00:05:00 UTC
            result = await client.get_kubernetes_info_events(
                from_time=from_time,
                to_time=to_time,
                max_events=10,
                api_client=mock_api_client
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "problem_analyses" in result
            assert len(result["problem_analyses"]) == 2
            assert result["problem_analyses"][0]["problem"] == "Pod Restart"
            assert result["problem_analyses"][1]["problem"] == "Pod Pending"
            assert "markdown_summary" in result
            assert "Kubernetes Events Analysis" in result["markdown_summary"]

            # Verify the API was called correctly
            mock_api_client.kubernetes_info_events.assert_called_once_with(
                to=to_time,
                var_from=from_time,
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_kubernetes_info_events_with_time_range(self, instana_credentials):
        """Test getting Kubernetes info events with natural language time range."""

        # Mock the API response
        mock_event = MagicMock()
        mock_event.to_dict.return_value = {
            "eventId": "event-123",
            "type": "kubernetes_info",
            "severity": 5,
            "start": 1625097600000,
            "end": 1625097900000,
            "entityId": "entity-123",
            "entityName": "pod-1",
            "entityLabel": "namespace-1/pod-1",
            "problem": "Pod Restart",
            "detail": "Pod restarted due to OOM",
            "fixSuggestion": "Increase memory limits"
        }

        mock_response = [mock_event]

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.kubernetes_info_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with natural language time range
            result = await client.get_kubernetes_info_events(
                time_range="last 24 hours",
                max_events=10,
                api_client=mock_api_client
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "problem_analyses" in result
            assert len(result["problem_analyses"]) == 1
            assert result["problem_analyses"][0]["problem"] == "Pod Restart"

            # Verify the API was called correctly with calculated timestamps
            expected_to_time = int(mock_now.timestamp.return_value * 1000)
            expected_from_time = expected_to_time - (24 * 60 * 60 * 1000)  # 24 hours earlier
            mock_api_client.kubernetes_info_events.assert_called_once_with(
                to=expected_to_time,
                var_from=expected_from_time,
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_kubernetes_info_events_empty_result(self, instana_credentials):
        """Test getting Kubernetes info events with empty result."""

        # Mock the API response to be empty
        mock_response = []

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.kubernetes_info_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            from_time = 1625097600000  # 2021-07-01 00:00:00 UTC
            to_time = 1625097900000    # 2021-07-01 00:05:00 UTC
            result = await client.get_kubernetes_info_events(
                from_time=from_time,
                to_time=to_time,
                api_client=mock_api_client
            )

            # Verify the result indicates no events found
            assert isinstance(result, dict)
            assert "analysis" in result
            assert "No Kubernetes events found" in result["analysis"]
            assert result["events_count"] == 0

            # Verify the API was called correctly
            mock_api_client.kubernetes_info_events.assert_called_once_with(
                to=to_time,
                var_from=from_time,
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_kubernetes_info_events_error(self, instana_credentials):
        """Test error handling when getting Kubernetes info events."""

        # Create a mock API client that raises an exception
        mock_api_client = MagicMock()
        mock_api_client.kubernetes_info_events.side_effect = Exception("API Error")

        # Create the client
        client = AgentMonitoringEventsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_kubernetes_info_events(
            from_time=1625097600000,
            to_time=1625097900000,
            api_client=mock_api_client
        )

        # Verify the result contains an error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "Failed to get Kubernetes info events" in result["error"]
        assert "API Error" in result["error"]

        # Verify the API was called
        mock_api_client.kubernetes_info_events.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_kubernetes_info_events_time_range_parsing(self, instana_credentials):
        """Test time range parsing in get_kubernetes_info_events."""

        # Mock the API response
        mock_response = []  # Empty response is fine for this test

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.kubernetes_info_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test different time range formats
            time_ranges = [
                "last few hours",
                "last 12 hours",
                "last 2 days",
                "last 1 week",
                "last 1 month",
                "unknown format"
            ]

            expected_hours = [24, 12, 48, 168, 720, 24]  # Expected hours for each time range

            for i, time_range in enumerate(time_ranges):
                # Reset the mock
                mock_api_client.kubernetes_info_events.reset_mock()

                # Test the method with this time range
                await client.get_kubernetes_info_events(
                    time_range=time_range,
                    api_client=mock_api_client
                )

                # Verify the API was called with correct timestamps
                expected_to_time = int(mock_now.timestamp.return_value * 1000)
                expected_from_time = expected_to_time - (expected_hours[i] * 60 * 60 * 1000)
                mock_api_client.kubernetes_info_events.assert_called_once_with(
                    to=expected_to_time,
                    var_from=expected_from_time,
                    window_size=None,
                    filter_event_updates=None,
                    exclude_triggered_before=None
                )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_agent_monitoring_events_success(self, instana_credentials):
        """Test getting agent monitoring events successfully."""

        # Mock the API response
        mock_event1 = MagicMock()
        mock_event1.to_dict.return_value = {
            "eventId": "event-123",
            "type": "agent_monitoring",
            "severity": 5,
            "start": 1625097600000,
            "end": 1625097900000,
            "entityId": "entity-123",
            "entityName": "host-1",
            "entityLabel": "host-1.example.com",
            "entityType": "host",
            "problem": "Monitoring issue: High CPU Usage",
        }

        mock_event2 = MagicMock()
        mock_event2.to_dict.return_value = {
            "eventId": "event-456",
            "type": "agent_monitoring",
            "severity": 7,
            "start": 1625097700000,
            "end": 1625097800000,
            "entityId": "entity-456",
            "entityName": "host-2",
            "entityLabel": "host-2.example.com",
            "entityType": "host",
            "problem": "Monitoring issue: Memory Pressure",
        }

        mock_response = [mock_event1, mock_event2]

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.agent_monitoring_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with from_time and to_time
            from_time = 1625097600000  # 2021-07-01 00:00:00 UTC
            to_time = 1625097900000    # 2021-07-01 00:05:00 UTC
            result = await client.get_agent_monitoring_events(
                from_time=from_time,
                to_time=to_time,
                max_events=10,
                api_client=mock_api_client
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "problem_analyses" in result
            assert len(result["problem_analyses"]) == 2
            assert result["problem_analyses"][0]["problem"] == "High CPU Usage"
            assert result["problem_analyses"][1]["problem"] == "Memory Pressure"
            assert "markdown_summary" in result
            assert "Agent Monitoring Events Analysis" in result["markdown_summary"]

            # Verify the API was called correctly
            mock_api_client.agent_monitoring_events.assert_called_once_with(
                to=to_time,
                var_from=from_time,
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_agent_monitoring_events_with_time_range(self, instana_credentials):
        """Test getting agent monitoring events with natural language time range."""

        # Mock the API response
        mock_event = MagicMock()
        mock_event.to_dict.return_value = {
            "eventId": "event-123",
            "type": "agent_monitoring",
            "severity": 5,
            "start": 1625097600000,
            "end": 1625097900000,
            "entityId": "entity-123",
            "entityName": "host-1",
            "entityLabel": "host-1.example.com",
            "entityType": "host",
            "problem": "Monitoring issue: High CPU Usage",
        }

        mock_response = [mock_event]

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.agent_monitoring_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method with natural language time range
            result = await client.get_agent_monitoring_events(
                time_range="last 24 hours",
                max_events=10,
                api_client=mock_api_client
            )

            # Verify the result
            assert isinstance(result, dict)
            assert "problem_analyses" in result
            assert len(result["problem_analyses"]) == 1
            assert result["problem_analyses"][0]["problem"] == "High CPU Usage"

            # Verify the API was called correctly with calculated timestamps
            expected_to_time = int(mock_now.timestamp.return_value * 1000)
            expected_from_time = expected_to_time - (24 * 60 * 60 * 1000)  # 24 hours earlier
            mock_api_client.agent_monitoring_events.assert_called_once_with(
                to=expected_to_time,
                var_from=expected_from_time,
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_agent_monitoring_events_empty_result(self, instana_credentials):
        """Test getting agent monitoring events with empty result."""

        # Mock the API response to be empty
        mock_response = []

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.agent_monitoring_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test the method
            from_time = 1625097600000  # 2021-07-01 00:00:00 UTC
            to_time = 1625097900000    # 2021-07-01 00:05:00 UTC
            result = await client.get_agent_monitoring_events(
                from_time=from_time,
                to_time=to_time,
                api_client=mock_api_client
            )

            # Verify the result indicates no events found
            assert isinstance(result, dict)
            assert "analysis" in result
            assert "No agent monitoring events found" in result["analysis"]
            assert result["events_count"] == 0

            # Verify the API was called correctly
            mock_api_client.agent_monitoring_events.assert_called_once_with(
                to=to_time,
                var_from=from_time,
                window_size=None,
                filter_event_updates=None,
                exclude_triggered_before=None
            )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_agent_monitoring_events_error(self, instana_credentials):
        """Test error handling when getting agent monitoring events."""

        # Create a mock API client that raises an exception
        mock_api_client = MagicMock()
        mock_api_client.agent_monitoring_events.side_effect = Exception("API Error")

        # Create the client
        client = AgentMonitoringEventsMCPTools(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )

        # Test the method
        result = await client.get_agent_monitoring_events(api_client=mock_api_client)

        # Verify the result contains the error message
        assert isinstance(result, dict)
        assert "error" in result
        assert "API Error" in result["error"]

        # Verify the API was called
        mock_api_client.agent_monitoring_events.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_comprehensive_time_range_parsing(self, instana_credentials):
        """Test comprehensive time range parsing in get_agent_monitoring_events."""

        # Mock the API response
        mock_response = []  # Empty response is fine for this test

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.agent_monitoring_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test different time range formats
            time_ranges = [
                "last few hours",
                "last 12 hours",
                "last 2 days",
                "last 1 week",
                "last 1 month",
                "unknown format"
            ]

            expected_hours = [24, 12, 48, 168, 720, 24]  # Expected hours for each time range

            for i, time_range in enumerate(time_ranges):
                # Reset the mock
                mock_api_client.agent_monitoring_events.reset_mock()

                # Test the method with this time range
                await client.get_agent_monitoring_events(
                    time_range=time_range,
                    api_client=mock_api_client
                )

                # Verify the API was called with correct timestamps
                expected_to_time = int(mock_now.timestamp.return_value * 1000)
                expected_from_time = expected_to_time - (expected_hours[i] * 60 * 60 * 1000)
                mock_api_client.agent_monitoring_events.assert_called_once_with(
                    to=expected_to_time,
                    var_from=expected_from_time,
                    window_size=None,
                    filter_event_updates=None,
                    exclude_triggered_before=None
                )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_edge_cases_and_defaults(self, instana_credentials):
        """Test edge cases and default values in get_agent_monitoring_events."""

        # Mock the API response
        mock_event = MagicMock()
        mock_event.to_dict.return_value = {
            "eventId": "event-123",
            "type": "agent_monitoring",
            "severity": 5,
            "start": 1625097600000,
            "end": 1625097900000,
            "entityId": "entity-123",
            "entityName": "host-1",
            "entityLabel": "host-1.example.com",
            "entityType": "host",
            "problem": "Monitoring issue: High CPU Usage",
        }

        mock_response = [mock_event]

        # Create a mock API client
        mock_api_client = MagicMock()
        mock_api_client.agent_monitoring_events.return_value = mock_response

        # Mock datetime.now() to return a fixed time
        with patch('src.event.events_tools.datetime') as mock_datetime:
            mock_now = MagicMock()
            mock_now.timestamp.return_value = 1625097900.0  # 2021-07-01 00:05:00 UTC
            mock_datetime.now.return_value = mock_now

            # Create the client
            client = AgentMonitoringEventsMCPTools(
                read_token=instana_credentials["api_token"],
                base_url=instana_credentials["base_url"]
            )

            # Test with no parameters (should use defaults)
            result1 = await client.get_agent_monitoring_events(api_client=mock_api_client)

            # Test with only to_time specified
            to_time = 1625097900000
            result2 = await client.get_agent_monitoring_events(to_time=to_time, api_client=mock_api_client)

            # Test with only from_time specified
            from_time = 1625097600000
            result3 = await client.get_agent_monitoring_events(from_time=from_time, api_client=mock_api_client)

            # Test with non-list response
            mock_api_client.agent_monitoring_events.return_value = mock_event  # Single event, not a list
            result4 = await client.get_agent_monitoring_events(api_client=mock_api_client)

            # Verify results
            assert isinstance(result1, dict)
            assert isinstance(result2, dict)
            assert isinstance(result3, dict)
            assert isinstance(result4, dict)


