"""
Unit tests for Synthetic Alert MCP Tools Module

Tests the SyntheticAlertMCPTools class which wraps the Instana
synthetic-alert-configuration API endpoints.
"""

import asyncio
import json
import logging
import sys
import unittest
from functools import wraps
from unittest.mock import MagicMock, Mock, patch

# Silence logging noise during tests
logging.basicConfig(level=logging.ERROR)

# ---------------------------------------------------------------------------
# Stub mcp/fastmcp and instana_client before any src import so that
# src.core.auth_helper's dotted imports (fastmcp.server.dependencies,
# instana_client.api_client, instana_client.configuration) resolve cleanly.
# Use setdefault so we don't clobber stubs set by sibling test files that
# may have been collected first in the same process.
# ---------------------------------------------------------------------------
_fastmcp_mock = MagicMock()
_fastmcp_server_mock = MagicMock()
_fastmcp_server_dep_mock = MagicMock()
_fastmcp_server_dep_mock.get_http_headers = MagicMock(return_value={})

sys.modules.setdefault('mcp', MagicMock())
sys.modules.setdefault('mcp.types', MagicMock())
sys.modules.setdefault('fastmcp', _fastmcp_mock)
sys.modules.setdefault('fastmcp.server', _fastmcp_server_mock)
sys.modules.setdefault('fastmcp.server.dependencies', _fastmcp_server_dep_mock)
sys.modules.setdefault('instana_client', MagicMock())
sys.modules.setdefault('instana_client.api', MagicMock())
sys.modules.setdefault('instana_client.api_client', MagicMock())
sys.modules.setdefault('instana_client.configuration', MagicMock())

# ---------------------------------------------------------------------------
# Mock the with_header_auth decorator so decorated methods receive
# self.alert_api as api_client instead of doing real auth.
# ---------------------------------------------------------------------------
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            kwargs['api_client'] = self.alert_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


# Stub out instana_client SDK modules required by synthetic_alert.py.
sys.modules.setdefault('instana_client', MagicMock())
sys.modules.setdefault('instana_client.api', MagicMock())
sys.modules['instana_client.api.synthetic_alert_configuration_api'] = MagicMock()
sys.modules.setdefault('instana_client.configuration', MagicMock())
sys.modules.setdefault('instana_client.api_client', MagicMock())
sys.modules.setdefault('instana_client.models', MagicMock())
sys.modules['instana_client.models.synthetic_alert_config'] = MagicMock()
# _build_config lazily imports these submodules; stub them since instana_client.models
# is a MagicMock (not a package) here. from_dict passes the input through unchanged.
sys.modules['instana_client.models.custom_payload_field'] = MagicMock(
    CustomPayloadField=MagicMock(from_dict=lambda d: d)
)
sys.modules['instana_client.models.tag_filter_expression_element'] = MagicMock(
    TagFilterExpressionElement=MagicMock(from_dict=lambda d: d)
)

mock_alert_api_class = MagicMock()
mock_alert_api_class.__name__ = 'SyntheticAlertConfigurationApi'
sys.modules['instana_client.api.synthetic_alert_configuration_api'].SyntheticAlertConfigurationApi = mock_alert_api_class

mock_alert_config_class = MagicMock()
mock_alert_config_class.__name__ = 'SyntheticAlertConfig'
sys.modules['instana_client.models.synthetic_alert_config'].SyntheticAlertConfig = mock_alert_config_class

with patch('src.core.utils.with_header_auth', mock_with_header_auth):
    from src.synthetic.synthetic_alert import SyntheticAlertMCPTools


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> SyntheticAlertMCPTools:
    client = SyntheticAlertMCPTools(
        read_token='test_token',
        base_url='https://test.instana.io',
    )
    client.alert_api = MagicMock()
    return client


def _mock_response(status: int, body):
    r = Mock()
    r.status = status
    r.data = json.dumps(body).encode('utf-8')
    r.headers = {'Content-Type': 'application/json'}
    return r


def _mock_text_response(status: int, text: str):
    r = Mock()
    r.status = status
    r.data = text.encode('utf-8')
    r.headers = {'Content-Type': 'text/plain'}
    return r


VALID_PAYLOAD = {
    'name': 'My Synthetic Alert',
    'description': 'Fires when test fails',
    'syntheticTestIds': ['test-abc'],
    'alertChannelIds': [],
    'customPayloadFields': [],
    'rule': {'alertType': 'failure', 'metricName': 'synthetic.metricsStatus'},
    'timeThreshold': {'type': 'violationsInSequence', 'violationsCount': 2},
    'tagFilterExpression': None,
}


# ---------------------------------------------------------------------------
# Tests — find_active_synthetic_alert_configs
# ---------------------------------------------------------------------------

class TestFindActiveSyntheticAlertConfigs(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_returns_configs_and_pagination_metadata(self):
        configs = [
            {'id': 'a1', 'name': 'Alert 1'},
            {'id': 'a2', 'name': 'Alert 2'},
            {'id': 'a3', 'name': 'Alert 3'},
        ]
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, configs)

        result = asyncio.run(self.client.find_active_synthetic_alert_configs())

        self.assertIn('configs', result)
        self.assertEqual(result['total'], 3)
        self.assertEqual(result['count'], 3)
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 50)
        self.assertEqual(result['total_pages'], 1)
        self.assertFalse(result['has_next'])
        self.assertFalse(result['has_previous'])

    def test_empty_list_returns_zero_count_message(self):
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, [])

        result = asyncio.run(self.client.find_active_synthetic_alert_configs())

        self.assertEqual(result['total'], 0)
        self.assertEqual(result['configs'], [])
        self.assertEqual(result['total_pages'], 0)
        self.assertFalse(result['has_next'])
        self.assertFalse(result['has_previous'])
        self.assertIn('No active', result['message'])

    def test_pagination_page2(self):
        configs = [{'id': f'a{i}'} for i in range(15)]
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, configs)

        result = asyncio.run(self.client.find_active_synthetic_alert_configs(page=2, page_size=10))

        self.assertEqual(result['page'], 2)
        self.assertEqual(result['count'], 5)
        self.assertEqual(result['total_pages'], 2)
        self.assertFalse(result['has_next'])
        self.assertTrue(result['has_previous'])

    def test_has_next_true_when_more_pages_exist(self):
        configs = [{'id': f'a{i}'} for i in range(25)]
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, configs)

        result = asyncio.run(self.client.find_active_synthetic_alert_configs(page=1, page_size=10))

        self.assertTrue(result['has_next'])
        self.assertFalse(result['has_previous'])
        self.assertEqual(result['count'], 10)
        self.assertEqual(result['total'], 25)
        self.assertEqual(result['total_pages'], 3)

    def test_has_next_false_on_exact_boundary(self):
        configs = [{'id': f'a{i}'} for i in range(20)]
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, configs)

        result = asyncio.run(self.client.find_active_synthetic_alert_configs(page=2, page_size=10))

        self.assertEqual(result['page'], 2)
        self.assertEqual(result['total_pages'], 2)
        self.assertFalse(result['has_next'])
        self.assertTrue(result['has_previous'])

    def test_api_error_returns_error_dict(self):
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(500, {'message': 'Internal error'})

        result = asyncio.run(self.client.find_active_synthetic_alert_configs())

        self.assertIn('error', result)
        self.assertIn('500', result['error'])

    def test_exception_is_caught(self):
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.side_effect = \
            RuntimeError('network failure')

        result = asyncio.run(self.client.find_active_synthetic_alert_configs())

        self.assertIn('error', result)
        self.assertIn('network failure', result['error'])

    def test_single_dict_response_is_wrapped_in_list(self):
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, {'id': 'a1', 'name': 'Single Alert'})

        result = asyncio.run(self.client.find_active_synthetic_alert_configs())

        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['configs']), 1)

    def test_pagination_out_of_range_page(self):
        configs = [{'id': f'a{i}'} for i in range(5)]
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, configs)

        result = asyncio.run(self.client.find_active_synthetic_alert_configs(page=99, page_size=10))

        # page is clamped to total_pages (1) — returns the last valid page instead of an empty result
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['total_pages'], 1)
        self.assertEqual(result['count'], 5)
        self.assertEqual(result['total'], 5)
        self.assertEqual(len(result['configs']), 5)
        self.assertFalse(result['has_next'])
        self.assertFalse(result['has_previous'])

    def test_pagination_invalid_page_and_page_size_fallbacks(self):
        configs = [{'id': f'a{i}'} for i in range(5)]
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, configs)

        result = asyncio.run(self.client.find_active_synthetic_alert_configs(page=0, page_size=-5))

        self.assertEqual(result['page'], 1)
        self.assertEqual(result['page_size'], 50)
        self.assertEqual(result['count'], 5)

    def test_synthetic_test_id_forwarded(self):
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, [])

        asyncio.run(self.client.find_active_synthetic_alert_configs(synthetic_test_id='test-xyz'))

        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.assert_called_once_with(
            synthetic_test_id='test-xyz',
            alert_ids=None,
        )

    def test_alert_ids_forwarded(self):
        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.return_value = \
            _mock_response(200, [])

        asyncio.run(self.client.find_active_synthetic_alert_configs(alert_ids=['id1', 'id2']))

        self.client.alert_api.find_active_synthetic_alert_configs_without_preload_content.assert_called_once_with(
            synthetic_test_id=None,
            alert_ids=['id1', 'id2'],
        )


# ---------------------------------------------------------------------------
# Tests — find_synthetic_alert_config
# ---------------------------------------------------------------------------

class TestFindSyntheticAlertConfig(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_success_returns_config(self):
        config = {'id': 'abc', 'name': 'My Alert'}
        self.client.alert_api.find_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(200, config)

        result = asyncio.run(self.client.find_synthetic_alert_config(id='abc'))

        self.assertEqual(result, config)

    def test_valid_on_is_forwarded(self):
        self.client.alert_api.find_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(200, {'id': 'abc'})

        asyncio.run(self.client.find_synthetic_alert_config(id='abc', valid_on=1710000000000))

        self.client.alert_api.find_synthetic_alert_config_without_preload_content.assert_called_once_with(
            id='abc',
            valid_on=1710000000000,
        )

    def test_api_error_propagated(self):
        self.client.alert_api.find_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(404, {'message': 'Not Found'})

        result = asyncio.run(self.client.find_synthetic_alert_config(id='abc'))

        self.assertIn('error', result)
        self.assertIn('404', result['error'])

    def test_exception_is_caught(self):
        self.client.alert_api.find_synthetic_alert_config_without_preload_content.side_effect = \
            Exception('timeout')

        result = asyncio.run(self.client.find_synthetic_alert_config(id='abc'))

        self.assertIn('error', result)
        self.assertIn('timeout', result['error'])

    def test_invalid_json_response_is_reported(self):
        resp = Mock(status=200, data=b"not json", headers={})
        self.client.alert_api.find_synthetic_alert_config_without_preload_content.return_value = resp

        result = asyncio.run(self.client.find_synthetic_alert_config(id="a"))

        self.assertIn("error", result)
        self.assertEqual(result["error"], "Invalid JSON from API")

    def test_empty_find_body_is_error(self):
        resp = Mock(status=200, data=b"", headers={})
        self.client.alert_api.find_synthetic_alert_config_without_preload_content.return_value = resp

        result = asyncio.run(self.client.find_synthetic_alert_config(id="a"))

        self.assertIn("error", result)
        self.assertIn("Empty response from API", result["error"])


# ---------------------------------------------------------------------------
# Tests — find_synthetic_alert_config_versions
# ---------------------------------------------------------------------------

class TestFindSyntheticAlertConfigVersions(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_success_returns_versions_and_count(self):
        versions = [{'id': 'abc', 'created': 1710000000000}, {'id': 'abc', 'created': 1700000000000}]
        self.client.alert_api.find_synthetic_alert_config_versions_without_preload_content.return_value = \
            _mock_response(200, versions)

        result = asyncio.run(self.client.find_synthetic_alert_config_versions(id='abc'))

        self.assertIn('versions', result)
        self.assertEqual(result['count'], 2)

    def test_id_forwarded_to_api(self):
        self.client.alert_api.find_synthetic_alert_config_versions_without_preload_content.return_value = \
            _mock_response(200, [])

        asyncio.run(self.client.find_synthetic_alert_config_versions(id='abc'))

        self.client.alert_api.find_synthetic_alert_config_versions_without_preload_content.assert_called_once_with(
            id='abc',
        )

    def test_api_error_propagated(self):
        self.client.alert_api.find_synthetic_alert_config_versions_without_preload_content.return_value = \
            _mock_response(403, {'message': 'Forbidden'})

        result = asyncio.run(self.client.find_synthetic_alert_config_versions(id='abc'))

        self.assertIn('error', result)
        self.assertIn('403', result['error'])

    def test_exception_is_caught(self):
        self.client.alert_api.find_synthetic_alert_config_versions_without_preload_content.side_effect = \
            Exception('connection reset')

        result = asyncio.run(self.client.find_synthetic_alert_config_versions(id='abc'))

        self.assertIn('error', result)
        self.assertIn('connection reset', result['error'])


# ---------------------------------------------------------------------------
# Tests — create_synthetic_alert_config
# ---------------------------------------------------------------------------

class TestCreateSyntheticAlertConfig(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_success_returns_created_config(self):
        created = {**VALID_PAYLOAD, 'id': 'new-id'}
        self.client.alert_api.create_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(200, created)

        result = asyncio.run(self.client.create_synthetic_alert_config(payload=VALID_PAYLOAD))

        self.assertEqual(result['id'], 'new-id')

    def test_success_with_json_string_payload(self):
        created = {**VALID_PAYLOAD, 'id': 'new-id-json'}
        self.client.alert_api.create_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(200, created)

        result = asyncio.run(self.client.create_synthetic_alert_config(payload=json.dumps(VALID_PAYLOAD)))

        self.assertEqual(result['id'], 'new-id-json')

    def test_invalid_payload_returns_parse_error(self):
        result = asyncio.run(self.client.create_synthetic_alert_config(payload=None))

        self.assertIn('error', result)

    def test_non_dict_payload_returns_error(self):
        result = asyncio.run(self.client.create_synthetic_alert_config(payload="[1, 2]"))

        self.assertIn('error', result)
        self.assertEqual(result['error'], 'payload must be a JSON object')

    def test_empty_create_body_returns_success(self):
        resp = Mock(status=200, data=b"", headers={})
        self.client.alert_api.create_synthetic_alert_config_without_preload_content.return_value = resp

        result = asyncio.run(self.client.create_synthetic_alert_config(payload=VALID_PAYLOAD))

        self.assertTrue(result.get('success'))

    def test_api_error_propagated(self):
        self.client.alert_api.create_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(400, {'message': 'Bad Request'})

        result = asyncio.run(self.client.create_synthetic_alert_config(payload=VALID_PAYLOAD))

        self.assertIn('error', result)
        self.assertIn('400', result['error'])

    def test_exception_is_caught(self):
        self.client.alert_api.create_synthetic_alert_config_without_preload_content.side_effect = \
            Exception('SDK failure')

        result = asyncio.run(self.client.create_synthetic_alert_config(payload=VALID_PAYLOAD))

        self.assertIn('error', result)
        self.assertIn('SDK failure', result['error'])


# ---------------------------------------------------------------------------
# Tests — update_synthetic_alert_config
# ---------------------------------------------------------------------------

class TestUpdateSyntheticAlertConfig(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_success_with_200_returns_updated_config(self):
        updated = {**VALID_PAYLOAD, 'id': 'abc', 'name': 'Updated Alert'}
        self.client.alert_api.update_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(200, updated)

        result = asyncio.run(self.client.update_synthetic_alert_config(id='abc', payload=VALID_PAYLOAD))

        self.assertEqual(result['name'], 'Updated Alert')

    def test_success_with_json_string_payload(self):
        updated = {**VALID_PAYLOAD, 'id': 'abc', 'name': 'Updated Alert via JSON'}
        self.client.alert_api.update_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(200, updated)

        result = asyncio.run(self.client.update_synthetic_alert_config(id='abc', payload=json.dumps(VALID_PAYLOAD)))

        self.assertEqual(result['name'], 'Updated Alert via JSON')

    def test_invalid_payload_returns_parse_error(self):
        result = asyncio.run(self.client.update_synthetic_alert_config(id='abc', payload=None))

        self.assertIn('error', result)

    def test_success_with_204_returns_success_dict(self):
        r = Mock()
        r.status = 204
        r.data = None
        self.client.alert_api.update_synthetic_alert_config_without_preload_content.return_value = r

        result = asyncio.run(self.client.update_synthetic_alert_config(id='abc', payload=VALID_PAYLOAD))

        self.assertTrue(result.get('success'))

    def test_api_error_propagated(self):
        self.client.alert_api.update_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(422, {'message': 'Unprocessable'})

        result = asyncio.run(self.client.update_synthetic_alert_config(id='abc', payload=VALID_PAYLOAD))

        self.assertIn('error', result)
        self.assertIn('422', result['error'])

    def test_exception_is_caught(self):
        self.client.alert_api.update_synthetic_alert_config_without_preload_content.side_effect = \
            Exception('update failed')

        result = asyncio.run(self.client.update_synthetic_alert_config(id='abc', payload=VALID_PAYLOAD))

        self.assertIn('error', result)
        self.assertIn('update failed', result['error'])


# ---------------------------------------------------------------------------
# Tests — delete_synthetic_alert_config
# ---------------------------------------------------------------------------

class TestDeleteSyntheticAlertConfig(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_success_returns_success_message(self):
        self.client.alert_api.delete_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(204, {})

        result = asyncio.run(self.client.delete_synthetic_alert_config(id='abc'))

        self.assertTrue(result.get('success'))
        self.assertIn('abc', result['message'])

    def test_api_error_propagated(self):
        self.client.alert_api.delete_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(404, {'message': 'Not Found'})

        result = asyncio.run(self.client.delete_synthetic_alert_config(id='abc'))

        self.assertIn('error', result)

    def test_non_json_success_body_is_still_success(self):
        self.client.alert_api.delete_synthetic_alert_config_without_preload_content.return_value = \
            _mock_text_response(200, 'OK')

        result = asyncio.run(self.client.delete_synthetic_alert_config(id='abc'))

        self.assertTrue(result.get('success'))


    def test_exception_is_caught(self):
        self.client.alert_api.delete_synthetic_alert_config_without_preload_content.side_effect = \
            Exception('delete error')

        result = asyncio.run(self.client.delete_synthetic_alert_config(id='abc'))

        self.assertIn('error', result)
        self.assertIn('delete error', result['error'])


# ---------------------------------------------------------------------------
# Tests — enable_synthetic_alert_config
# ---------------------------------------------------------------------------

class TestEnableSyntheticAlertConfig(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_success_returns_success_message(self):
        self.client.alert_api.enable_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(204, {})

        result = asyncio.run(self.client.enable_synthetic_alert_config(id='abc'))

        self.assertTrue(result.get('success'))
        self.assertIn('abc', result['message'])

    def test_api_error_propagated(self):
        self.client.alert_api.enable_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(400, {'message': 'Bad Request'})

        result = asyncio.run(self.client.enable_synthetic_alert_config(id='abc'))

        self.assertIn('error', result)

    def test_non_json_success_body_is_still_success(self):
        self.client.alert_api.enable_synthetic_alert_config_without_preload_content.return_value = \
            _mock_text_response(200, 'OK')

        result = asyncio.run(self.client.enable_synthetic_alert_config(id='abc'))

        self.assertTrue(result.get('success'))

    def test_exception_is_caught(self):
        self.client.alert_api.enable_synthetic_alert_config_without_preload_content.side_effect = \
            Exception('enable error')

        result = asyncio.run(self.client.enable_synthetic_alert_config(id='abc'))

        self.assertIn('error', result)


# ---------------------------------------------------------------------------
# Tests — disable_synthetic_alert_config
# ---------------------------------------------------------------------------

class TestDisableSyntheticAlertConfig(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_success_returns_success_message(self):
        self.client.alert_api.disable_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(204, {})

        result = asyncio.run(self.client.disable_synthetic_alert_config(id='abc'))

        self.assertTrue(result.get('success'))
        self.assertIn('abc', result['message'])

    def test_api_error_propagated(self):
        self.client.alert_api.disable_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(400, {'message': 'Bad Request'})

        result = asyncio.run(self.client.disable_synthetic_alert_config(id='abc'))

        self.assertIn('error', result)

    def test_non_json_success_body_is_still_success(self):
        self.client.alert_api.disable_synthetic_alert_config_without_preload_content.return_value = \
            _mock_text_response(200, 'OK')

        result = asyncio.run(self.client.disable_synthetic_alert_config(id='abc'))

        self.assertTrue(result.get('success'))

    def test_exception_is_caught(self):
        self.client.alert_api.disable_synthetic_alert_config_without_preload_content.side_effect = \
            Exception('disable error')

        result = asyncio.run(self.client.disable_synthetic_alert_config(id='abc'))

        self.assertIn('error', result)


# ---------------------------------------------------------------------------
# Tests — restore_synthetic_alert_config
# ---------------------------------------------------------------------------

class TestRestoreSyntheticAlertConfig(unittest.TestCase):

    def setUp(self):
        self.client = _make_client()

    def test_success_returns_success_message(self):
        self.client.alert_api.restore_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(204, {})

        result = asyncio.run(self.client.restore_synthetic_alert_config(id='abc', created=1710000000000))

        self.assertTrue(result.get('success'))
        self.assertIn('abc', result['message'])
        self.assertIn('1710000000000', result['message'])

    def test_id_and_created_forwarded(self):
        self.client.alert_api.restore_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(204, {})

        asyncio.run(self.client.restore_synthetic_alert_config(id='abc', created=1710000000000))

        self.client.alert_api.restore_synthetic_alert_config_without_preload_content.assert_called_once_with(
            id='abc',
            created=1710000000000,
        )

    def test_api_error_propagated(self):
        self.client.alert_api.restore_synthetic_alert_config_without_preload_content.return_value = \
            _mock_response(404, {'message': 'Not Found'})

        result = asyncio.run(self.client.restore_synthetic_alert_config(id='abc', created=1710000000000))

        self.assertIn('error', result)
        self.assertIn('404', result['error'])

    def test_non_json_success_body_is_still_success(self):
        self.client.alert_api.restore_synthetic_alert_config_without_preload_content.return_value = \
            _mock_text_response(200, 'OK')

        result = asyncio.run(self.client.restore_synthetic_alert_config(id='abc', created=1710000000000))

        self.assertTrue(result.get('success'))

    def test_exception_is_caught(self):
        self.client.alert_api.restore_synthetic_alert_config_without_preload_content.side_effect = \
            Exception('restore failed')

        result = asyncio.run(self.client.restore_synthetic_alert_config(id='abc', created=1710000000000))

        self.assertIn('error', result)
        self.assertIn('restore failed', result['error'])


# ---------------------------------------------------------------------------
# Tests — timeout from sdk_call_with_keepalive (returns an error dict, not a response)
# ---------------------------------------------------------------------------

TIMEOUT_DICT = {
    'error': 'Instana API call timed out after 180s (op). The Instana server did not respond in time.',
    'operation': 'op',
    'resource_type': 'alert',
    'timeout_seconds': 180,
}


class TestSdkTimeoutHandling(unittest.TestCase):
    """sdk_call_with_keepalive returns a dict on timeout; it must not be treated as a response."""

    def setUp(self):
        self.client = _make_client()
        patcher = patch(
            'src.synthetic.synthetic_alert.sdk_call_with_keepalive',
            side_effect=self._timeout,
        )
        self.mock_keepalive = patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    async def _timeout(*args, **_kwargs):
        # Close the un-awaited SDK coroutine the way a cancelled call would.
        if args and asyncio.iscoroutine(args[0]):
            args[0].close()
        return dict(TIMEOUT_DICT)

    def _assert_timeout_error(self, result):
        self.assertIn('timed out', result['error'])
        self.assertEqual(result['timeout_seconds'], 180)
        self.assertNotIn('status', result['error'])
        self.assertNotIn('Failed to', result['error'])

    def test_find_timeout_returns_timeout_error(self):
        result = asyncio.run(self.client.find_synthetic_alert_config(id='abc'))

        self._assert_timeout_error(result)

    def test_find_active_timeout_returns_timeout_error(self):
        result = asyncio.run(self.client.find_active_synthetic_alert_configs())

        self._assert_timeout_error(result)

    def test_delete_timeout_returns_timeout_error(self):
        result = asyncio.run(self.client.delete_synthetic_alert_config(id='abc'))

        self._assert_timeout_error(result)

    def test_create_timeout_returns_timeout_error(self):
        result = asyncio.run(self.client.create_synthetic_alert_config(payload=VALID_PAYLOAD))

        self._assert_timeout_error(result)

    def test_update_timeout_returns_timeout_error(self):
        result = asyncio.run(self.client.update_synthetic_alert_config(id='abc', payload=VALID_PAYLOAD))

        self._assert_timeout_error(result)

