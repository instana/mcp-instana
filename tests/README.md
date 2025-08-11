# Unit Tests for mcp-instana

This directory contains unit tests for the mcp-instana project. This document provides comprehensive information about the test structure, organization, execution, and extension.

## Quick Start with UV

The project now supports running tests using `uv run` commands for better dependency management and faster execution:

### Basic Test Commands

```bash
# Run all tests
uv run test

# Run all tests with verbose output
uv run test -v

# Run all tests with coverage
uv run test-coverage

# Run all tests with HTML coverage report
uv run test-coverage --html

# Run all tests with XML coverage report
uv run test-coverage --xml
```

### Running Specific Tests

```bash
# Run tests for a specific module
uv run test tests/application/test_application_alert_config.py

# Run tests in a specific directory
uv run test tests/application

# Run a specific test class
uv run python -m unittest tests.application.test_application_alert_config.TestApplicationAlertMCPTools

# Run a specific test method
uv run python -m unittest tests.application.test_application_alert_config.TestApplicationAlertMCPTools.test_find_application_alert_config_success
```

### Coverage with Custom Options

```bash
# Include specific patterns
uv run test-coverage --include "src/application/*"

# Exclude specific patterns
uv run test-coverage --omit "src/prompts/*"

# Combine options
uv run test-coverage --html --include "src/application/*" --omit "tests/*"
```

## Test Structure and Organization

The test suite is organized as follows:

- `tests/` - Root directory for all tests
  - `__init__.py` - Makes the tests directory a Python package
  - `README.md` - This documentation file
  - `run_all_tests.py` - Script to run all tests without coverage
  - `run_all_tests_with_coverage.py` - Script to run all tests with coverage reporting
  - `application/` - Tests for application modules in `src/application/`
    - `test_application_alert_config.py` - Tests for application alert configuration tools
    - `test_application_analyze.py` - Tests for application analysis tools
    - `test_application_catalog.py` - Tests for application catalog tools
    - `test_application_metrics.py` - Tests for application metrics tools
    - `test_application_resources.py` - Tests for application resource tools
    - `test_application_topology.py` - Tests for application topology tools
  - `core/` - Tests for core modules in `src/core/`
    - `test_server.py` - Tests for the main MCP server module
    - `test_utils.py` - Tests for core utility functions
  - `event/` - Tests for event modules in `src/event/`
    - `test_events_tools.py` - Tests for event handling tools
  - `infrastructure/` - Tests for infrastructure modules in `src/infrastructure/`
    - `test_infrastructure_analyze.py` - Tests for infrastructure analysis tools
    - `test_infrastructure_catalog.py` - Tests for infrastructure catalog tools
    - `test_infrastructure_metrics.py` - Tests for infrastructure metrics tools
    - `test_infrastructure_resources.py` - Tests for infrastructure resource tools
    - `test_infrastructure_topology.py` - Tests for infrastructure topology tools
  - `log/` - Tests for log modules in `src/log/`
    - `test_log_alert_configuration.py` - Tests for log alert configuration tools
  - `prompts/` - Tests for prompt modules in `src/prompts/`
    - `test_mcp_prompts.py` - Tests for MCP prompt functionality

### Test Hierarchy

Tests follow a hierarchical structure that mirrors the source code:

1. **Module Level**: Each source module has a corresponding test module (e.g., `src/core/server.py` → `tests/core/test_server.py`)
2. **Class Level**: Each class in a module has a corresponding test class (e.g., `ApplicationAlertMCPTools` → `TestApplicationAlertMCPTools`)
3. **Method Level**: Each method in a class has one or more test methods (e.g., `find_application_alert_config` → `test_find_application_alert_config_success`, `test_find_application_alert_config_missing_id`, etc.)

### Test Types

The test suite includes:

1. **Synchronous Tests**: Standard unittest tests
2. **Asynchronous Tests**: Tests for async functions using asyncio
3. **Mock Tests**: Tests that use unittest.mock to mock external dependencies and SDK calls

## Running Tests

### Environment Setup

Before running tests, set up your environment:

1. **Set required environment variables** (if not already set in your environment):
   ```bash
   export INSTANA_API_TOKEN="your_api_token"
   export INSTANA_BASE_URL="https://your-instana-instance.io"
   export INSTANA_ENABLED_TOOLS="all"  # or specific tools like "events,infra"
   ```

### Running All Tests

To run all tests without coverage:

```bash
# From the project root
cd mcp-instana
uv run test
```

With verbose output:

```bash
uv run test -v
```

### Running Tests with Coverage

To run all tests with coverage reporting:

```bash
# From the project root
cd mcp-instana
uv run test-coverage
```

#### Coverage Report Options

The coverage tool supports different report formats:

1. **Console Report** (default):
   ```bash
   uv run test-coverage
   ```

2. **HTML Report**:
   ```bash
   uv run test-coverage --html
   ```
   This generates an HTML report in the `htmlcov` directory, which you can view in a browser.

3. **XML Report**:
   ```bash
   uv run test-coverage --xml
   ```
   This generates a `coverage.xml` file, useful for CI/CD integration.

#### Coverage Configuration Options

You can customize which files are included in or excluded from coverage:

```bash
# Include specific patterns
uv run test-coverage --include "src/application/*"

# Exclude specific patterns
uv run test-coverage --omit "src/prompts/*"

# Combine options
uv run test-coverage --html --include "src/application/*" --omit "tests/*"
```

By default, coverage includes all files in the `src/` directory and excludes files in the `tests/` directory and `setup.py`.

### Running Specific Tests

#### Running Tests for a Specific Module

```bash
# Run tests for a specific module
uv run test tests/application/test_application_alert_config.py
```

#### Running Tests in a Specific Directory

```bash
# Run all tests in the application directory
uv run test tests/application
```

#### Running a Specific Test Class or Method

To run a specific test class:

```bash
# Using unittest directly
uv run python -m unittest tests.application.test_application_alert_config.TestApplicationAlertMCPTools
```

To run a specific test method:

```bash
# Using unittest directly
uv run python -m unittest tests.application.test_application_alert_config.TestApplicationAlertMCPTools.test_find_application_alert_config_success
```

## Test Configuration

### Test Runner Configuration

The test runners (`run_all_tests.py` and `run_all_tests_with_coverage.py`) support the following command-line arguments:

- `test_path`: Optional path to a specific test module, file, or directory
- `-v, --verbose`: Run tests in verbose mode
- `--html`: Generate HTML coverage report (coverage only)
- `--xml`: Generate XML coverage report (coverage only)
- `--include`: File patterns to include in coverage (can be used multiple times)
- `--omit`: File patterns to omit from coverage (can be used multiple times)

### Environment Variables

The tests use the following environment variables:

- `INSTANA_API_TOKEN`: API token for Instana
- `INSTANA_BASE_URL`: Base URL for the Instana API
- `INSTANA_ENABLED_TOOLS`: Comma-separated list of enabled tool categories (e.g., "events,infra") or "all"

## Interpreting Test Results

### Test Output

The test runner provides the following information:

1. **Test Progress**: For each test module, it shows which tests are running
2. **Test Summary**: At the end, it shows the total number of tests run and the time taken
3. **Test Status**: Shows whether all tests passed or if there were failures
4. **Failed Tests**: Lists any failed tests with their module and method names

Example output:

```
Ran 472 tests in 1.239s

✅ All Tests OK
```

Or with failures:

```
Ran 472 tests in 1.345s

❌ 5 test(s) failed.

=== FAILED TESTS ===
📁 test_application_alert_config
  ↳ TestApplicationAlertMCPTools.test_find_application_alert_config_success
  ↳ TestApplicationAlertMCPTools.test_create_application_alert_config_success

📁 test_infrastructure_topology
  ↳ TestInfrastructureTopologyMCPTools.test_get_topology_error
===================
```

### Coverage Report Interpretation

The coverage report shows:

1. **Module Coverage**: Percentage of code covered in each module
2. **Line Numbers**: Which specific lines are not covered
3. **Total Coverage**: Overall percentage of code covered

Example console output:

```
Name                                            Stmts   Miss  Cover
-------------------------------------------------------------------
src/application/application_alert_config.py       120     15    88%
src/infrastructure/infrastructure_metrics.py       95      8    92%
src/core/server.py                                 150     22    85%
-------------------------------------------------------------------
TOTAL                                              365     45    88%
```

In HTML reports, uncovered lines are highlighted in red, partially covered lines in yellow, and fully covered lines in green.

## Test Categories and Tags

Tests are categorized by the module they test. The main categories are:

1. **Core Tests**: Tests for the core MCP server and utility functionality
   - Located in `tests/core/`
   - Test classes: `TestMCPServer`, `TestBaseInstanaClient`, etc.

2. **Application Tests**: Tests for application monitoring tools
   - Located in `tests/application/`
   - Test classes: `TestApplicationAlertMCPTools`, `TestApplicationMetricsMCPTools`, etc.

3. **Infrastructure Tests**: Tests for infrastructure monitoring tools
   - Located in `tests/infrastructure/`
   - Test classes: `TestInfrastructureTopologyMCPTools`, `TestInfrastructureMetricsMCPTools`, etc.

4. **Event Tests**: Tests for event handling tools
   - Located in `tests/event/`
   - Test classes: `TestEventsMCPTools`

5. **Log Tests**: Tests for log monitoring and alert configuration
   - Located in `tests/log/`
   - Test classes: `TestLogAlertConfigurationMCPTools`

6. **Prompt Tests**: Tests for MCP prompt functionality
   - Located in `tests/prompts/`
   - Test classes: `TestMcpPrompts`

Within each test class, test methods follow a naming convention that indicates what they test:

- `test_<method_name>_success`: Tests the successful execution path
- `test_<method_name>_error`: Tests error handling
- `test_<method_name>_missing_<param>`: Tests behavior when a required parameter is missing
- `test_<method_name>_with_<condition>`: Tests behavior under specific conditions
- `test_<method_name>_sdk_error`: Tests SDK-level error handling

## Troubleshooting Common Test Failures

### Import Errors

If you see import errors like `ModuleNotFoundError: No module named 'src'`, ensure:

1. You're running tests from the project root directory
2. The project root is in your Python path
3. You're using the correct `uv run` commands

### Mock Errors

If tests fail with errors related to mocks:

1. Check that you're mocking the correct path
2. Ensure the mock is set up before the code under test is called
3. Verify that the mock is configured to return appropriate values
4. For SDK mocks, ensure `.to_dict()` method returns the expected dictionary

Example fix:

```python
# Incorrect
mock_result = MagicMock()
self.client.application_alert_configuration_api.find_application_alert_config.return_value = mock_result

# Correct
mock_result = MagicMock()
mock_result.to_dict.return_value = {"id": "alert1", "name": "Test Alert"}
self.client.application_alert_configuration_api.find_application_alert_config.return_value = mock_result
```

### Async Test Failures

If async tests fail:

1. Ensure you're using proper async/await syntax
2. Check that async methods are properly awaited
3. Use `asyncio.get_event_loop().run_until_complete()` for running async tests in sync test methods

Example fix:

```python
def run_async(self, coro):
    return asyncio.get_event_loop().run_until_complete(coro)

def test_async_method_success(self):
    result = self.run_async(self.client.async_method())
    self.assertEqual(result, expected_value)
```

### Decorator and SDK Mock Issues

If tests fail due to decorator or SDK mocking issues:

1. Ensure decorators are mocked before module import
2. Use global mocks for decorators that are applied at import time
3. Clear `side_effect` before setting `return_value` in success tests

Example fix:

```python
# Mock decorators before import
with patch('src.core.utils.with_header_auth', mock_decorator):
    with patch('src.core.utils.register_as_tool', mock_decorator):
        from src.application.application_alert_config import ApplicationAlertMCPTools

# In test methods, clear side effects
self.mock_api.method_name.side_effect = None  # Clear any previous side_effect
self.mock_api.method_name.return_value = expected_result
```

### Environment Variable Issues

If tests fail due to missing environment variables:

1. Check that required environment variables are set
2. Ensure the variables have the correct values
3. Consider adding default values in the test setup

## Extending the Test Suite

### Adding New Test Files

When adding a new module:

1. Create a corresponding test file in the appropriate `tests/` subdirectory
2. Follow the naming convention: `test_<module_name>.py`

Example:

```python
"""
Unit tests for the NewModule class
"""

import asyncio
import unittest
from unittest.mock import patch, MagicMock

# Import the class to test
from src.application.new_module import NewModule

class TestNewModule(unittest.TestCase):
    """Test the NewModule class"""

    def setUp(self):
        """Set up test fixtures"""
        self.read_token = "test_token"
        self.base_url = "https://test.instana.io"
        self.client = NewModule(read_token=self.read_token, base_url=self.base_url)
        
    def run_async(self, coro):
        """Helper method to run async functions in sync tests"""
        return asyncio.get_event_loop().run_until_complete(coro)
        
    def test_method_success(self):
        """Test successful execution of a method"""
        # Test code here
        pass
```

### Adding Tests for Async Functions

For async functions, use the `run_async` helper method:

```python
def test_async_method(self):
    """Test an async method"""
    # Set up mocks
    mock_result = {"key": "value"}
    mock_obj = MagicMock()
    mock_obj.to_dict.return_value = mock_result
    self.client.api.method.return_value = mock_obj
    
    # Test async code
    result = self.run_async(self.client.async_method())
    self.assertEqual(result, mock_result)
```

### Test Best Practices

1. **Test Independence**: Each test should be independent and not rely on the state from other tests
2. **Mock External Dependencies**: Use `unittest.mock` to mock external dependencies, especially SDK calls
3. **Test Error Cases**: Include tests for error conditions and edge cases
4. **Clear Test Names**: Use descriptive test method names that indicate what is being tested
5. **Setup and Teardown**: Use `setUp` and `tearDown` methods for common setup and cleanup
6. **Assert Meaningful Values**: Make assertions that verify the actual behavior, not just that code runs
7. **Mock SDK Responses**: Always mock SDK responses with proper `.to_dict()` return values
8. **Clear Side Effects**: Clear `side_effect` before setting `return_value` in success tests

### Coverage Goals

Aim for high test coverage:

1. **Line Coverage**: Aim for at least 85% line coverage
2. **Branch Coverage**: Test both true and false conditions for if statements
3. **Exception Handling**: Test both normal execution and exception paths
4. **SDK Integration**: Test both successful SDK calls and error conditions

Use the coverage report to identify areas that need more tests.

## Test Dependencies

The tests use the following libraries:

- `unittest`: Standard Python testing framework
- `unittest.mock`: For mocking external dependencies
- `coverage`: For measuring code coverage
- `asyncio`: For testing async functions

No additional test libraries are required.

## Import Structure

The tests import modules directly from the `src` directory:

```python
from src.application.application_alert_config import ApplicationAlertMCPTools
from src.infrastructure.infrastructure_topology import InfrastructureTopologyMCPTools
from src.core.utils import BaseInstanaClient
```

Make sure the project root directory is in your Python path when running the tests, which is handled automatically by the `uv run` commands.
