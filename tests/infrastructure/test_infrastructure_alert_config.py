"""
Unit tests for InfrastructureAlertConfigMCPTools
"""

import asyncio
import importlib
import json
import logging
import os
import sys
import types
import unittest
from functools import wraps
from unittest.mock import MagicMock

# Silence logging noise during tests
logging.basicConfig(level=logging.ERROR)
_logger = logging.getLogger('src.infrastructure.infrastructure_alert_config')
_logger.handlers = []
_logger.addHandler(logging.NullHandler())
_logger.propagate = False

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# ---------------------------------------------------------------------------
# Stub out the instana_client SDK so no real package is needed.
# Must happen before any src imports so the module-level SDK imports resolve.
#
# IMPORTANT: instana_client and instana_client.api must be registered as real
# module objects (types.ModuleType), NOT as MagicMock instances.  Python uses
# sys.modules to resolve dotted package paths; if the parent entry is a plain
# MagicMock, subsequent imports of sibling sub-modules from other test files
# that share the same process fail with:
#   ModuleNotFoundError: 'instana_client.api' is not a package
# Using types.ModuleType preserves the package semantics while still allowing
# attribute access on the stubs.
# ---------------------------------------------------------------------------

def _make_module(name: str) -> types.ModuleType:
    """Return a ModuleType stub that also behaves like a MagicMock for attrs."""
    mod = types.ModuleType(name)
    mod.__path__ = []   # marks it as a package
    mod.__package__ = name
    return mod


# Only register the stubs if instana_client hasn't been imported yet; this
# makes the file safe to run both in isolation and as part of the full suite.
if 'instana_client' not in sys.modules:
    sys.modules['instana_client'] = _make_module('instana_client')
if 'instana_client.api' not in sys.modules:
    sys.modules['instana_client.api'] = _make_module('instana_client.api')

sys.modules['instana_client.api.infrastructure_alert_configuration_api'] = MagicMock()
sys.modules['instana_client.models'] = sys.modules.get('instana_client.models') or _make_module('instana_client.models')
sys.modules['instana_client.models.infra_alert_config'] = MagicMock()
sys.modules['instana_client.configuration'] = sys.modules.get('instana_client.configuration') or MagicMock()
sys.modules['instana_client.api_client'] = sys.modules.get('instana_client.api_client') or MagicMock()

mock_alert_api_class = MagicMock()
mock_alert_api_class.__name__ = 'InfrastructureAlertConfigurationApi'
sys.modules[
    'instana_client.api.infrastructure_alert_configuration_api'
].InfrastructureAlertConfigurationApi = mock_alert_api_class

# ---------------------------------------------------------------------------
# Mock the with_header_auth decorator so it injects self.alert_api as
# api_client instead of doing real auth.
# Must be defined before src.core.utils is imported so we can replace the
# attribute on the already-imported module object.
# ---------------------------------------------------------------------------
def mock_with_header_auth(api_class, allow_mock=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            kwargs['api_client'] = self.alert_api
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

# Import src.core.utils now so we can patch its with_header_auth attribute,
# then restore it immediately after the module-under-test is loaded so the
# patch does not leak into other test modules that run in the same process.
import src.core.utils as _core_utils

_original_with_header_auth = _core_utils.with_header_auth
_core_utils.with_header_auth = mock_with_header_auth

# Now safe to import and reload the module under test
import src.infrastructure.infrastructure_alert_config as _alert_mod

_alert_mod = importlib.reload(_alert_mod)
InfrastructureAlertConfigMCPTools = _alert_mod.InfrastructureAlertConfigMCPTools

# Restore the real decorator so later test modules see the original behaviour
_core_utils.with_header_auth = _original_with_header_auth


def _make_client():
    """Instantiate a fresh InfrastructureAlertConfigMCPTools for each test."""
    return InfrastructureAlertConfigMCPTools(
        read_token='test_token',
        base_url='https://test.instana.io',
    )


def _mock_response(status: int, body: dict):
    """Build a fake HTTPResponse-like object."""
    r = MagicMock()
    r.status = status
    r.data = json.dumps(body).encode('utf-8')
    r.headers = {'Content-Type': 'application/json'}
    return r


# ---------------------------------------------------------------------------
# Minimal valid payload for create / update
# ---------------------------------------------------------------------------
VALID_PAYLOAD = {
    'name': 'High CPU',
    'description': 'CPU above threshold',
    'granularity': 600000,
    'groupBy': [],
    'tagFilterExpression': {'type': 'EXPRESSION', 'logicalOperator': 'AND', 'elements': []},
    'timeThreshold': {'type': 'violationsInSequence', 'timeWindow': 600000},
}


class TestInfraAlertConfigValidation(unittest.TestCase):
    """Tests for the static validation helpers — no SDK calls needed."""

    def setUp(self):
        self.client = _make_client()

    # ---- _validate_alert_payload ----------------------------------------

    def test_validate_missing_payload(self):
        result = self.client._validate_alert_payload(None, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(result['elicitation_needed'])
        self.assertIn('payload', result['message'])

    def test_validate_payload_not_dict(self):
        result = self.client._validate_alert_payload('bad', 'create')
        self.assertIsNotNone(result)
        self.assertIn('dict', result['message'])

    def test_validate_missing_name(self):
        p = dict(VALID_PAYLOAD)
        del p['name']
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('name' in e for e in result['api_error']))

    def test_validate_missing_description(self):
        p = dict(VALID_PAYLOAD)
        del p['description']
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('description' in e for e in result['api_error']))

    def test_validate_invalid_granularity(self):
        p = {**VALID_PAYLOAD, 'granularity': 99999}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('granularity' in e for e in result['api_error']))

    def test_validate_granularity_not_int(self):
        p = {**VALID_PAYLOAD, 'granularity': '600000'}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('granularity' in e for e in result['api_error']))

    def test_validate_missing_group_by(self):
        p = dict(VALID_PAYLOAD)
        del p['groupBy']
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('groupBy' in e for e in result['api_error']))

    def test_validate_missing_tag_filter_expression(self):
        p = dict(VALID_PAYLOAD)
        del p['tagFilterExpression']
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('tagFilterExpression' in e for e in result['api_error']))

    def test_validate_missing_time_threshold(self):
        p = dict(VALID_PAYLOAD)
        del p['timeThreshold']
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('timeThreshold' in e for e in result['api_error']))

    def test_validate_name_non_string(self):
        p = {**VALID_PAYLOAD, 'name': 123}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('name' in e for e in result['api_error']))

    def test_validate_name_too_long(self):
        p = {**VALID_PAYLOAD, 'name': 'a' * 257}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('name' in e for e in result['api_error']))

    def test_validate_description_non_string(self):
        p = {**VALID_PAYLOAD, 'description': 123}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('description' in e for e in result['api_error']))

    def test_validate_group_by_non_list(self):
        p = {**VALID_PAYLOAD, 'groupBy': 'not-a-list'}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('groupBy' in e for e in result['api_error']))

    def test_validate_invalid_severity(self):
        p = {**VALID_PAYLOAD, 'severity': 7}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('severity' in e for e in result['api_error']))

    def test_validate_invalid_evaluation_type(self):
        p = {**VALID_PAYLOAD, 'evaluationType': 'WRONG'}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNotNone(result)
        self.assertTrue(any('evaluationType' in e for e in result['api_error']))

    def test_validate_valid_payload_returns_none(self):
        result = self.client._validate_alert_payload(VALID_PAYLOAD, 'create')
        self.assertIsNone(result)

    def test_validate_valid_payload_with_optional_fields(self):
        p = {**VALID_PAYLOAD, 'severity': 10, 'evaluationType': 'PER_ENTITY', 'triggering': True}
        result = self.client._validate_alert_payload(p, 'create')
        self.assertIsNone(result)

    # ---- _preflight --------------------------------------------------------

    def test_preflight_find_missing_id(self):
        result = self.client._preflight('find', id=None, created=None)
        self.assertIsNotNone(result)
        self.assertTrue(any('id' in e for e in result['api_error']))

    def test_preflight_update_missing_id(self):
        result = self.client._preflight('update', id=None, created=None)
        self.assertIsNotNone(result)
        self.assertTrue(any('id' in e for e in result['api_error']))

    def test_preflight_delete_missing_id(self):
        result = self.client._preflight('delete', id=None, created=None)
        self.assertIsNotNone(result)

    def test_preflight_restore_missing_created(self):
        result = self.client._preflight('restore', id='abc', created=None)
        self.assertIsNotNone(result)
        self.assertTrue(any('created' in e for e in result['api_error']))

    def test_preflight_restore_invalid_created(self):
        result = self.client._preflight('restore', id='abc', created=-1)
        self.assertIsNotNone(result)
        self.assertTrue(any('created' in e for e in result['api_error']))

    def test_preflight_find_active_no_requirements(self):
        # find_active has no required params
        result = self.client._preflight('find_active', id=None, created=None)
        self.assertIsNone(result)

    def test_preflight_find_with_id_passes(self):
        result = self.client._preflight('find', id='abc123', created=None)
        self.assertIsNone(result)

    def test_preflight_restore_with_all_params_passes(self):
        result = self.client._preflight('restore', id='abc', created=1710000000000)
        self.assertIsNone(result)

    # ---- _parse_payload ----------------------------------------------------

    def test_parse_payload_dict_passthrough(self):
        p = {'name': 'test'}
        self.assertEqual(self.client._parse_payload(p), p)

    def test_parse_payload_json_string(self):
        p = '{"name": "test"}'
        self.assertEqual(self.client._parse_payload(p), {'name': 'test'})

    def test_parse_payload_none(self):
        self.assertIsNone(self.client._parse_payload(None))

    def test_parse_payload_invalid_string(self):
        with self.assertRaises(ValueError) as ctx:
            self.client._parse_payload('not json at all :::')
        self.assertIn("payload could not be parsed", str(ctx.exception))
        self.assertIn("not json at all :::", str(ctx.exception))


class TestInfraAlertConfigDispatcher(unittest.TestCase):
    """Tests for execute_alert_config_operation — the public dispatcher."""

    def setUp(self):
        self.client = _make_client()
        self.client.alert_api = MagicMock()

    def test_unknown_operation_returns_error(self):
        result = asyncio.run(self.client.execute_alert_config_operation(operation='nonexistent'))
        self.assertIn('error', result)
        self.assertIn('nonexistent', result['error'])

    def test_preflight_blocks_find_without_id(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find', id=None
        ))
        self.assertTrue(result.get('elicitation_needed'))
        self.assertTrue(any('id' in e for e in result['api_error']))

    def test_preflight_blocks_restore_without_created(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='restore', id='abc', created=None
        ))
        self.assertTrue(result.get('elicitation_needed'))

    def test_payload_validation_blocks_create_with_bad_payload(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='create', payload={'name': 'x'}  # missing required fields
        ))
        self.assertTrue(result.get('elicitation_needed'))

    def test_payload_validation_blocks_update_with_bad_payload(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='update', id='abc', payload={'name': 'x'}
        ))
        self.assertTrue(result.get('elicitation_needed'))

    def test_execute_dispatcher_exception_handling(self):
        self.client._find = MagicMock(side_effect=Exception('dispatcher failure'))
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find', id='abc'
        ))
        self.assertIn('error', result)
        self.assertIn('dispatcher failure', result['error'])


class TestInfraAlertConfigOperations(unittest.TestCase):
    """Tests for each individual operation method — SDK API is mocked."""

    def setUp(self):
        self.client = _make_client()
        self.client.alert_api = MagicMock()

    # ---- find_active -------------------------------------------------------

    def test_find_active_success(self):
        configs = [{'id': 'c1', 'name': 'Alert 1'}, {'id': 'c2', 'name': 'Alert 2'}]
        self.client.alert_api.find_active_infra_alert_configs_without_preload_content.return_value = \
            _mock_response(200, configs)

        result = asyncio.run(self.client.execute_alert_config_operation(operation='find_active'))

        self.assertIn('configs', result)
        self.assertEqual(result['total'], 2)
        self.assertEqual(len(result['configs']), 2)

    def test_find_active_empty(self):
        self.client.alert_api.find_active_infra_alert_configs_without_preload_content.return_value = \
            _mock_response(200, [])

        result = asyncio.run(self.client.execute_alert_config_operation(operation='find_active'))

        self.assertEqual(result['total'], 0)
        self.assertIn('No active', result['message'])

    def test_find_active_with_alert_ids(self):
        self.client.alert_api.find_active_infra_alert_configs_without_preload_content.return_value = \
            _mock_response(200, [{'id': 'c1'}])

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find_active', alert_ids=['c1']
        ))

        self.client.alert_api.find_active_infra_alert_configs_without_preload_content.assert_called_once_with(
            alert_ids=['c1']
        )
        self.assertEqual(result['total'], 1)

    def test_find_active_api_error(self):
        self.client.alert_api.find_active_infra_alert_configs_without_preload_content.return_value = \
            _mock_response(500, {'message': 'Internal error'})

        result = asyncio.run(self.client.execute_alert_config_operation(operation='find_active'))
        self.assertIn('error', result)

    def test_find_active_single_dict_result(self):
        self.client.alert_api.find_active_infra_alert_configs_without_preload_content.return_value = \
            _mock_response(200, {'id': 'c1', 'name': 'Alert 1'})

        result = asyncio.run(self.client.execute_alert_config_operation(operation='find_active'))
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['configs']), 1)

    def test_find_active_exception(self):
        self.client.alert_api.find_active_infra_alert_configs_without_preload_content.side_effect = Exception('network err')

        result = asyncio.run(self.client.execute_alert_config_operation(operation='find_active'))
        self.assertIn('error', result)

    # ---- find --------------------------------------------------------------

    def test_find_success(self):
        config = {'id': 'abc', 'name': 'My Alert'}
        mock_result = MagicMock()
        mock_result.to_dict.return_value = config
        self.client.alert_api.find_infra_alert_config.return_value = mock_result

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find', id='abc'
        ))

        self.assertEqual(result, config)
        self.client.alert_api.find_infra_alert_config.assert_called_once_with(id='abc', valid_on=None)

    def test_find_with_valid_on(self):
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {'id': 'abc'}
        self.client.alert_api.find_infra_alert_config.return_value = mock_result

        asyncio.run(self.client.execute_alert_config_operation(
            operation='find', id='abc', valid_on=1710000000000
        ))

        self.client.alert_api.find_infra_alert_config.assert_called_once_with(
            id='abc', valid_on=1710000000000
        )

    def test_find_dict_result(self):
        self.client.alert_api.find_infra_alert_config.return_value = {'id': 'abc'}

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find', id='abc'
        ))
        self.assertEqual(result, {'id': 'abc'})

    def test_find_other_result_type(self):
        self.client.alert_api.find_infra_alert_config.return_value = "some_string_result"

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find', id='abc'
        ))
        self.assertEqual(result, {'data': 'some_string_result'})

    def test_find_api_exception(self):
        self.client.alert_api.find_infra_alert_config.side_effect = Exception('not found')

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find', id='abc'
        ))
        self.assertIn('error', result)

    # ---- find_versions -----------------------------------------------------

    def test_find_versions_success(self):
        versions = [{'id': 'abc', 'created': 1710000000000}]
        self.client.alert_api.find_infra_alert_config_versions.return_value = versions

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find_versions', id='abc'
        ))

        self.assertIn('versions', result)
        self.client.alert_api.find_infra_alert_config_versions.assert_called_once_with(id='abc')

    def test_find_versions_with_to_dict_and_dict(self):
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {'id': 'abc', 'v': 1}
        self.client.alert_api.find_infra_alert_config_versions.return_value = mock_obj

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find_versions', id='abc'
        ))
        self.assertEqual(result, {'id': 'abc', 'v': 1})

        self.client.alert_api.find_infra_alert_config_versions.return_value = {'id': 'abc', 'v': 2}
        result2 = asyncio.run(self.client.execute_alert_config_operation(
            operation='find_versions', id='abc'
        ))
        self.assertEqual(result2, {'id': 'abc', 'v': 2})

        self.client.alert_api.find_infra_alert_config_versions.return_value = "raw_val"
        result3 = asyncio.run(self.client.execute_alert_config_operation(
            operation='find_versions', id='abc'
        ))
        self.assertEqual(result3, {'data': 'raw_val'})

    def test_find_versions_exception(self):
        self.client.alert_api.find_infra_alert_config_versions.side_effect = Exception('versions err')

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='find_versions', id='abc'
        ))
        self.assertIn('error', result)

    # ---- create ------------------------------------------------------------

    def test_create_success(self):
        created_config = {**VALID_PAYLOAD, 'id': 'new-id'}
        self.client.alert_api.create_infra_alert_config_without_preload_content.return_value = \
            _mock_response(201, created_config)

        # InfraAlertConfig is already mocked via sys.modules at module level
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='create', payload=VALID_PAYLOAD
        ))

        # No elicitation — payload was valid and SDK mock returned 201
        self.assertNotIn('elicitation_needed', result)

    def test_create_blocked_by_validation(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='create', payload={}
        ))
        self.assertTrue(result.get('elicitation_needed'))

    def test_create_defaults_injected(self):
        """customPayloadFields and alertChannelIds are defaulted when absent."""
        payload_no_defaults = dict(VALID_PAYLOAD)
        # ensure keys absent
        payload_no_defaults.pop('customPayloadFields', None)
        payload_no_defaults.pop('alertChannelIds', None)

        captured = {}

        def capture_call(**kwargs):
            captured['payload'] = kwargs.get('infra_alert_config')
            return _mock_response(201, {**VALID_PAYLOAD, 'id': 'x'})

        self.client.alert_api.create_infra_alert_config_without_preload_content.side_effect = \
            lambda **kw: _mock_response(201, {**VALID_PAYLOAD, 'id': 'x'})

        asyncio.run(self.client.execute_alert_config_operation(
            operation='create', payload=payload_no_defaults
        ))
        # No error means the defaults were filled in and from_dict didn't blow up
        # (InfraAlertConfig.from_dict is mocked via sys.modules)

    def test_create_api_error_response(self):
        self.client.alert_api.create_infra_alert_config_without_preload_content.return_value = \
            _mock_response(400, {'errors': ['Bad request']})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='create', payload=VALID_PAYLOAD
        ))
        self.assertIn('error', result)

    def test_create_exception(self):
        self.client.alert_api.create_infra_alert_config_without_preload_content.side_effect = Exception('SDK error')

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='create', payload=VALID_PAYLOAD
        ))
        self.assertIn('error', result)

    # ---- update ------------------------------------------------------------

    def test_update_success(self):
        updated_config = {**VALID_PAYLOAD, 'id': 'abc'}
        self.client.alert_api.update_infra_alert_config_without_preload_content.return_value = \
            _mock_response(200, updated_config)

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='update', id='abc', payload=VALID_PAYLOAD
        ))
        self.assertEqual(result, updated_config)

    def test_update_defaults_injected(self):
        payload_no_defaults = dict(VALID_PAYLOAD)
        payload_no_defaults.pop('customPayloadFields', None)
        payload_no_defaults.pop('alertChannelIds', None)

        self.client.alert_api.update_infra_alert_config_without_preload_content.return_value = \
            _mock_response(200, {**VALID_PAYLOAD, 'id': 'abc'})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='update', id='abc', payload=payload_no_defaults
        ))
        self.assertNotIn('elicitation_needed', result)

    def test_update_empty_response_204(self):
        r = MagicMock()
        r.status = 204
        r.data = b''
        r.headers = {}
        self.client.alert_api.update_infra_alert_config_without_preload_content.return_value = r

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='update', id='abc', payload=VALID_PAYLOAD
        ))
        self.assertTrue(result.get('success'))

    def test_update_api_error(self):
        self.client.alert_api.update_infra_alert_config_without_preload_content.return_value = \
            _mock_response(500, {'error': 'failed'})

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='update', id='abc', payload=VALID_PAYLOAD
        ))
        self.assertIn('error', result)

    def test_update_exception(self):
        self.client.alert_api.update_infra_alert_config_without_preload_content.side_effect = Exception('update crash')

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='update', id='abc', payload=VALID_PAYLOAD
        ))
        self.assertIn('error', result)

    def test_update_blocked_by_missing_id(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='update', id=None, payload=VALID_PAYLOAD
        ))
        self.assertTrue(result.get('elicitation_needed'))
        self.assertTrue(any('id' in e for e in result['api_error']))

    def test_update_blocked_by_bad_payload(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='update', id='abc', payload={'name': 'only'}
        ))
        self.assertTrue(result.get('elicitation_needed'))

    # ---- delete ------------------------------------------------------------

    def test_delete_success(self):
        self.client.alert_api.delete_infra_alert_config.return_value = None

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='delete', id='abc'
        ))

        self.assertTrue(result.get('success'))
        self.assertIn('abc', result['message'])
        self.client.alert_api.find_infra_alert_config.assert_not_called()
        self.client.alert_api.delete_infra_alert_config.assert_called_once_with(id='abc')

    def test_delete_blocked_by_missing_id(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='delete', id=None
        ))
        self.assertTrue(result.get('elicitation_needed'))

    def test_delete_not_found(self):
        self.client.alert_api.delete_infra_alert_config.return_value = _mock_response(
            404, {'message': 'Alert config not found'}
        )

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='delete', id='missing'
        ))

        self.assertIn('error', result)
        self.client.alert_api.delete_infra_alert_config.assert_called_once_with(id='missing')

    def test_delete_api_exception(self):
        self.client.alert_api.delete_infra_alert_config.side_effect = Exception('forbidden')

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='delete', id='abc'
        ))
        self.assertIn('error', result)

    # ---- enable / disable --------------------------------------------------

    def test_enable_success(self):
        self.client.alert_api.enable_infra_alert_config.return_value = None

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='enable', id='abc'
        ))

        self.assertIn('success', result)
        self.client.alert_api.enable_infra_alert_config.assert_called_once_with(id='abc')

    def test_enable_returns_to_dict_and_dict(self):
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {'id': 'abc', 'enabled': True}
        self.client.alert_api.enable_infra_alert_config.return_value = mock_obj

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='enable', id='abc'
        ))
        self.assertEqual(result, {'id': 'abc', 'enabled': True})

        self.client.alert_api.enable_infra_alert_config.return_value = {'id': 'abc', 'enabled': True}
        result2 = asyncio.run(self.client.execute_alert_config_operation(
            operation='enable', id='abc'
        ))
        self.assertEqual(result2, {'id': 'abc', 'enabled': True})

    def test_enable_exception(self):
        self.client.alert_api.enable_infra_alert_config.side_effect = Exception('enable failed')

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='enable', id='abc'
        ))
        self.assertIn('error', result)

    def test_disable_success(self):
        self.client.alert_api.disable_infra_alert_config.return_value = None

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='disable', id='abc'
        ))

        self.assertIn('success', result)
        self.client.alert_api.disable_infra_alert_config.assert_called_once_with(id='abc')

    def test_disable_returns_to_dict_and_dict(self):
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {'id': 'abc', 'enabled': False}
        self.client.alert_api.disable_infra_alert_config.return_value = mock_obj

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='disable', id='abc'
        ))
        self.assertEqual(result, {'id': 'abc', 'enabled': False})

        self.client.alert_api.disable_infra_alert_config.return_value = {'id': 'abc', 'enabled': False}
        result2 = asyncio.run(self.client.execute_alert_config_operation(
            operation='disable', id='abc'
        ))
        self.assertEqual(result2, {'id': 'abc', 'enabled': False})

    def test_disable_exception(self):
        self.client.alert_api.disable_infra_alert_config.side_effect = Exception('disable failed')

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='disable', id='abc'
        ))
        self.assertIn('error', result)

    def test_enable_blocked_by_missing_id(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='enable', id=None
        ))
        self.assertTrue(result.get('elicitation_needed'))

    # ---- restore -----------------------------------------------------------

    def test_restore_success(self):
        self.client.alert_api.restore_infra_alert_config.return_value = None

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='restore', id='abc', created=1710000000000
        ))

        self.assertIn('success', result)
        self.client.alert_api.restore_infra_alert_config.assert_called_once_with(
            id='abc', created=1710000000000
        )

    def test_restore_returns_to_dict_and_dict(self):
        mock_obj = MagicMock()
        mock_obj.to_dict.return_value = {'id': 'abc', 'restored': True}
        self.client.alert_api.restore_infra_alert_config.return_value = mock_obj

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='restore', id='abc', created=1710000000000
        ))
        self.assertEqual(result, {'id': 'abc', 'restored': True})

        self.client.alert_api.restore_infra_alert_config.return_value = {'id': 'abc', 'restored': True}
        result2 = asyncio.run(self.client.execute_alert_config_operation(
            operation='restore', id='abc', created=1710000000000
        ))
        self.assertEqual(result2, {'id': 'abc', 'restored': True})

    def test_restore_exception(self):
        self.client.alert_api.restore_infra_alert_config.side_effect = Exception('restore failed')

        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='restore', id='abc', created=1710000000000
        ))
        self.assertIn('error', result)

    def test_restore_blocked_by_missing_created(self):
        result = asyncio.run(self.client.execute_alert_config_operation(
            operation='restore', id='abc', created=None
        ))
        self.assertTrue(result.get('elicitation_needed'))

if __name__ == '__main__':
    unittest.main()
