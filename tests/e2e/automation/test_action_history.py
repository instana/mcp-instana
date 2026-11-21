"""
E2E tests for Automation Action History MCP Tools
"""

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest


def create_action_history_client(instana_credentials):
    """Dynamically import and create Action History client"""
    module = importlib.import_module("src.automation.action_history")
    module = importlib.reload(module)
    return module.ActionHistoryMCPTools(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"],
    )


def _model(payload):
    """SDK-model-like object exposing to_dict()."""
    obj = MagicMock()
    obj.to_dict.return_value = payload
    return obj


def _valid_submit_payload():
    return {"actionId": "act-1", "hostId": "host-1", "async": "true", "timeout": "600"}


class TestActionHistoryE2E:
    """End-to-end tests for Automation Action History MCP Tools"""

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_initialization(self, instana_credentials):
        client = create_action_history_client(instana_credentials)
        assert client.read_token == instana_credentials["api_token"]
        assert client.base_url == instana_credentials["base_url"]

    # ---------------------------------------------------------------- submit
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_submit_automation_action_success_with_to_dict(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.add_action_instance.return_value = _model({"runId": "run-1"})
        client = create_action_history_client(instana_credentials)

        result = await client.submit_automation_action(payload=_valid_submit_payload(), api_client=mock_api)

        assert result == {"runId": "run-1"}
        mock_api.add_action_instance.assert_called_once()
        assert "action_instance_request" in mock_api.add_action_instance.call_args.kwargs

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_submit_automation_action_plain_result_and_empty_default(self, instana_credentials):
        client = create_action_history_client(instana_credentials)

        mock_api = MagicMock()
        mock_api.add_action_instance.return_value = {"runId": "run-2"}
        result = await client.submit_automation_action(payload=_valid_submit_payload(), api_client=mock_api)
        assert result == {"runId": "run-2"}

        mock_api.add_action_instance.return_value = None
        result = await client.submit_automation_action(payload=_valid_submit_payload(), api_client=mock_api)
        assert result == {"success": True, "message": "Automation action submitted successfully"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("make_payload", [
        json.dumps,
        lambda p: json.dumps(p).replace('"', "'"),
        repr,
    ], ids=["json", "single-quoted", "python-literal"])
    async def test_submit_automation_action_string_payload_formats(self, instana_credentials, make_payload):
        mock_api = MagicMock()
        mock_api.add_action_instance.return_value = _model({"runId": "run-1"})
        client = create_action_history_client(instana_credentials)

        result = await client.submit_automation_action(
            payload=make_payload(_valid_submit_payload()), api_client=mock_api
        )

        assert result == {"runId": "run-1"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_submit_automation_action_validation_errors(self, instana_credentials):
        client = create_action_history_client(instana_credentials)

        assert await client.submit_automation_action(payload={}, api_client=MagicMock()) == {
            "error": "payload is required"
        }

        result = await client.submit_automation_action(payload="{not: valid", api_client=MagicMock())
        assert "Invalid payload format" in result["error"]
        assert result["payload"] == "{not: valid"

        result = await client.submit_automation_action(payload={"hostId": "h"}, api_client=MagicMock())
        assert result == {"error": "Missing required field: actionId"}

        result = await client.submit_automation_action(payload={"actionId": "a"}, api_client=MagicMock())
        assert result == {"error": "Missing required field: hostId"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_submit_automation_action_invalid_model_fields(self, instana_credentials):
        client = create_action_history_client(instana_credentials)

        result = await client.submit_automation_action(
            payload={"actionId": "a", "hostId": "h", "inputParameters": "not-a-list"},
            api_client=MagicMock(),
        )

        assert "Failed to create config object" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_submit_automation_action_import_error(self, instana_credentials):
        client = create_action_history_client(instana_credentials)

        with patch.dict("sys.modules", {"instana_client.models.action_instance_request": None}):
            result = await client.submit_automation_action(
                payload=_valid_submit_payload(), api_client=MagicMock()
            )

        assert "Failed to import ActionInstanceRequest" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_submit_automation_action_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.add_action_instance.side_effect = Exception("Boom")
        client = create_action_history_client(instana_credentials)

        result = await client.submit_automation_action(payload=_valid_submit_payload(), api_client=mock_api)

        assert "Failed to submit automation action" in result["error"]
        assert "Boom" in result["error"]

    # ---------------------------------------------------------------- instance details
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_instance_details_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_instance.return_value = _model({"id": "run-1", "status": "SUCCESS"})
        client = create_action_history_client(instana_credentials)

        result = await client.get_action_instance_details(
            action_instance_id="run-1", window_size=600000, to=1710658800000, api_client=mock_api
        )

        assert result == {"id": "run-1", "status": "SUCCESS"}
        mock_api.get_action_instance.assert_called_once_with(
            action_instance_id="run-1", window_size=600000, to=1710658800000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_instance_details_plain_and_empty_result(self, instana_credentials):
        client = create_action_history_client(instana_credentials)
        mock_api = MagicMock()

        mock_api.get_action_instance.return_value = {"id": "run-1"}
        result = await client.get_action_instance_details(action_instance_id="run-1", api_client=mock_api)
        assert result == {"id": "run-1"}

        mock_api.get_action_instance.return_value = None
        result = await client.get_action_instance_details(action_instance_id="run-1", api_client=mock_api)
        assert result == {"success": True, "message": "Action instance details retrieved successfully"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    @pytest.mark.parametrize("bad_id", ["", "   ", None])
    async def test_get_action_instance_details_missing_id(self, instana_credentials, bad_id):
        mock_api = MagicMock()
        client = create_action_history_client(instana_credentials)

        result = await client.get_action_instance_details(action_instance_id=bad_id, api_client=mock_api)

        assert result["elicitation_needed"] is True
        assert "action_instance_id" in result["reason"]
        mock_api.get_action_instance.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_instance_details_invalid_window_size(self, instana_credentials):
        client = create_action_history_client(instana_credentials)

        result = await client.get_action_instance_details(
            action_instance_id="run-1", window_size="big", api_client=MagicMock()
        )
        assert result["elicitation_needed"] is True
        assert "must be a positive integer" in result["api_error"][0]

        result = await client.get_action_instance_details(
            action_instance_id="run-1", window_size=-1, api_client=MagicMock()
        )
        assert result["elicitation_needed"] is True
        assert "must be ≥ 0" in result["api_error"][0]

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_get_action_instance_details_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_instance.side_effect = Exception("Boom")
        client = create_action_history_client(instana_credentials)

        result = await client.get_action_instance_details(action_instance_id="run-1", api_client=mock_api)

        assert "Failed to get action instance details" in result["error"]

    # ---------------------------------------------------------------- list
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_action_instances_success_with_filters(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_instances.return_value = _model({"items": [{"id": "run-1"}], "totalHits": 1})
        client = create_action_history_client(instana_credentials)
        filters = {
            "window_size": 3600000,
            "to": 1710658800000,
            "page": 2,
            "page_size": 25,
            "target_snapshot_id": "snap-1",
            "event_id": "evt-1",
            "event_specification_id": "spec-1",
            "search": "restart",
            "types": ["SCRIPT"],
            "action_statuses": ["SUCCESS", "FAILED"],
            "order_by": "startedAt",
            "order_direction": "DESC",
        }

        result = await client.list_action_instances(filters=filters, api_client=mock_api)

        assert result == {"items": [{"id": "run-1"}], "totalHits": 1}
        mock_api.get_action_instances.assert_called_once_with(**filters)

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_action_instances_defaults_and_empty_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_instances.return_value = None
        client = create_action_history_client(instana_credentials)

        result = await client.list_action_instances(api_client=mock_api)

        assert result == {"success": True, "message": "Action instances retrieved successfully"}
        kwargs = mock_api.get_action_instances.call_args.kwargs
        assert all(value is None for value in kwargs.values())

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_action_instances_plain_dict_result(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_instances.return_value = {"items": []}
        client = create_action_history_client(instana_credentials)

        result = await client.list_action_instances(filters={}, api_client=mock_api)

        assert result == {"items": []}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_action_instances_preflight_errors(self, instana_credentials):
        mock_api = MagicMock()
        client = create_action_history_client(instana_credentials)

        result = await client.list_action_instances(
            filters={"page": "x", "page_size": "y", "window_size": "z", "order_direction": "UP"},
            api_client=mock_api,
        )
        assert result["elicitation_needed"] is True
        assert len(result["api_error"]) == 4
        assert "page: must be an integer" in result["api_error"][0]
        assert "page_size: must be an integer" in result["api_error"][1]
        assert "window_size: must be a positive integer" in result["api_error"][2]
        assert "order_direction: 'UP'" in result["api_error"][3]

        result = await client.list_action_instances(
            filters={"page": 0, "page_size": 0, "window_size": -1}, api_client=mock_api
        )
        assert len(result["api_error"]) == 3
        assert "must be ≥ 1 (1-based" in result["api_error"][0]
        assert "page_size: 0 must be ≥ 1" in result["api_error"][1]
        assert "window_size: -1 must be ≥ 0" in result["api_error"][2]

        mock_api.get_action_instances.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_list_action_instances_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.get_action_instances.side_effect = Exception("Boom")
        client = create_action_history_client(instana_credentials)

        result = await client.list_action_instances(api_client=mock_api)

        assert "Failed to list action instances" in result["error"]

    # ---------------------------------------------------------------- delete
    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_action_instance_success(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.delete_action_instance.return_value = _model({"deleted": True})
        client = create_action_history_client(instana_credentials)

        result = await client.delete_action_instance(
            action_instance_id="run-1", from_time=1710658800000, to_time=1710662400000, api_client=mock_api
        )

        assert result == {"deleted": True}
        mock_api.delete_action_instance.assert_called_once_with(
            action_instance_id="run-1", var_from=1710658800000, to=1710662400000
        )

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_action_instance_plain_and_empty_result(self, instana_credentials):
        client = create_action_history_client(instana_credentials)
        mock_api = MagicMock()

        mock_api.delete_action_instance.return_value = {"ok": 1}
        result = await client.delete_action_instance(
            action_instance_id="run-1", from_time=1, to_time=2, api_client=mock_api
        )
        assert result == {"ok": 1}

        mock_api.delete_action_instance.return_value = None
        result = await client.delete_action_instance(
            action_instance_id="run-1", from_time=1, to_time=2, api_client=mock_api
        )
        assert result == {"success": True, "message": "Action instance deleted successfully"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_action_instance_validation(self, instana_credentials):
        client = create_action_history_client(instana_credentials)

        assert await client.delete_action_instance(
            action_instance_id="", from_time=1, to_time=2, api_client=MagicMock()
        ) == {"error": "action_instance_id is required"}
        assert await client.delete_action_instance(
            action_instance_id="run-1", from_time=0, to_time=2, api_client=MagicMock()
        ) == {"error": "from_time is required"}
        assert await client.delete_action_instance(
            action_instance_id="run-1", from_time=1, to_time=0, api_client=MagicMock()
        ) == {"error": "to_time is required"}

    @pytest.mark.asyncio
    @pytest.mark.mocked
    async def test_delete_action_instance_exception(self, instana_credentials):
        mock_api = MagicMock()
        mock_api.delete_action_instance.side_effect = Exception("Boom")
        client = create_action_history_client(instana_credentials)

        result = await client.delete_action_instance(
            action_instance_id="run-1", from_time=1, to_time=2, api_client=mock_api
        )

        assert "Failed to delete action instance" in result["error"]
