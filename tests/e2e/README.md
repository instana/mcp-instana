# End-to-End (E2E) Testing Framework

The project includes a comprehensive E2E testing framework to validate the complete functionality of the MCP server and its integration with Instana APIs.

## Table of Contents
- [Test Structure](#test-structure)
- [Test Types](#test-types)
- [Prerequisites](#prerequisites)
- [Running Tests](#running-tests)
- [Test Configuration](#test-configuration)
- [Writing New Tests](#writing-new-tests)
- [Best Practices](#best-practices)
- [Troubleshooting Tests](#troubleshooting-tests)

## Test Structure

```
tests/
├── e2e/                          # E2E test directory
│   ├── __init__.py              # Package initialization
│   ├── conftest.py              # Shared fixtures and configuration
│   ├── pytest.ini              # Pytest configuration
│   ├── run_e2e_tests.py        # Custom test runner script
│   ├── README.md               # This file - E2E test documentation
│   ├── test_application_catalog.py      # Application catalog tests
│   ├── test_application_resources.py    # Application resources tests
│   └── test_mcp_server_integration.py  # MCP server integration tests
└── test_mcp_server.py          # Unit tests (existing)
```

## Test Types

### 1. Mocked Tests (`@pytest.mark.mocked`)
- **Purpose**: Test application logic without external API calls
- **Speed**: Fast execution (< 1 second)
- **Reliability**: Deterministic, no network dependencies
- **Use Case**: Development, CI/CD, regression testing

### 2. Real API Tests (`@pytest.mark.real_api`)
- **Purpose**: Test against actual Instana API endpoints
- **Speed**: Slower (depends on API response time)
- **Reliability**: May fail due to network/API issues
- **Use Case**: Integration testing, API validation

### 3. Integration Tests (`@pytest.mark.integration`)
- **Purpose**: Test complete workflows and tool chains
- **Speed**: Medium (multiple tool executions)
- **Reliability**: High (mocked dependencies)
- **Use Case**: End-to-end workflow validation

## Prerequisites

### Required Dependencies
```bash
# Install testing dependencies
uv add pytest pytest-asyncio pytest-mock pytest-cov aiohttp
```

### For Real API Tests
```bash
# Set environment variables
export INSTANA_API_TOKEN="your_actual_token"
export INSTANA_BASE_URL="https://your-instana-instance.instana.io"
export RUN_REAL_API_TESTS="true"
```

## Running Tests

### Quick Start Commands

| **Purpose** | **Command** |
|-------------|-------------|
| **All mocked tests** | `uv run tests/e2e/run_e2e_tests.py mocked` |
| **All real API tests** | `uv run tests/e2e/run_e2e_tests.py real` |
| **All tests** | `uv run tests/e2e/run_e2e_tests.py all` |
| **Verbose output** | `uv run tests/e2e/run_e2e_tests.py mocked -v` |
| **With coverage** | `uv run tests/e2e/run_e2e_tests.py mocked -c` |

### Direct Pytest Commands

```bash
# Run all E2E tests
uv run -m pytest tests/e2e/ -v

# Run only mocked tests
uv run -m pytest tests/e2e/ -m mocked -v

# Run only real API tests
uv run -m pytest tests/e2e/ -m real_api -v

# Run specific test file
uv run -m pytest tests/e2e/test_application_catalog.py -v

# Run specific test class
uv run -m pytest tests/e2e/test_application_catalog.py::TestApplicationCatalogE2E -v

# Run specific test method
uv run -m pytest tests/e2e/test_mcp_server_integration.py::TestMCPServerIntegrationE2E::test_multiple_tool_execution_flow -v
```

### Advanced Commands

```bash
# Run with coverage report
uv run -m pytest tests/e2e/ -m mocked --cov=src --cov-report=html --cov-report=term

# Run with debug output
uv run -m pytest tests/e2e/ -m mocked -v -s

# Run tests in parallel (requires pytest-xdist)
uv run -m pytest tests/e2e/ -m mocked -n auto

# Stop on first failure
uv run -m pytest tests/e2e/ -m mocked -x
```

## Test Configuration

### Pytest Configuration (`tests/e2e/pytest.ini`)
```ini
[tool:pytest]
# Test discovery
testpaths = tests/e2e
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    e2e: mark test as end-to-end test
    real_api: mark test as requiring real API access
    mocked: mark test as using mocked responses
    slow: mark test as slow running
    integration: mark test as integration test

# Async support
asyncio_mode = auto

# Test output
addopts =
    -v
    --tb=short
    --strict-markers
    --disable-warnings
```

### Environment Variables
```bash
# Test environment
TEST_TIMEOUT=30                    # Test timeout in seconds
TEST_RETRY_ATTEMPTS=3              # Retry attempts for flaky tests
INSTANA_ENABLED_TOOLS=all          # Tools to enable for testing

# Real API testing
INSTANA_API_TOKEN=your_token       # Instana API token
INSTANA_BASE_URL=your_url          # Instana base URL
RUN_REAL_API_TESTS=true            # Enable real API tests
```

## Writing New Tests

### Test Structure Template
```python
@pytest.mark.asyncio
@pytest.mark.mocked  # or @pytest.mark.real_api
async def test_your_feature(self, instana_credentials):
    """Test description."""
    
    # Arrange: Set up test data and mocks
    from src.client.your_client import YourClient
    client = YourClient(
        read_token=instana_credentials["api_token"],
        base_url=instana_credentials["base_url"]
    )
    
    # Mock the SDK method (for mocked tests)
    client.sdk_method = AsyncMock(return_value={"data": "test"})
    
    # Act: Execute the method under test
    result = await client.your_method()
    
    # Assert: Verify the results
    assert isinstance(result, dict)
    assert "data" in result
    assert result["data"] == "test"
```

### Mocking Best Practices

```python
# ✅ Good: Mock at the instance level
client = YourClient(token, url)
client.sdk_method = AsyncMock(return_value={"data": "test"})

# ❌ Avoid: Mocking at class level (can interfere with other tests)
with patch('src.client.YourClient.sdk_method') as mock:
    # This can cause issues with async methods
```

### Real API Test Template
```python
@pytest.mark.asyncio
@pytest.mark.real_api
async def test_real_api_integration(self, instana_credentials):
    """Test with real Instana API."""
    
    # Skip if no real credentials
    if not instana_credentials["api_token"] or instana_credentials["api_token"] == "test_token":
        pytest.skip("Real API credentials not available")
    
    try:
        client = YourClient(
            read_token=instana_credentials["api_token"],
            base_url=instana_credentials["base_url"]
        )
        
        result = await client.your_method()
        
        # Assert structure, not specific content
        assert isinstance(result, dict)
        # Don't assert specific values as they depend on real data
        
    except Exception as e:
        pytest.fail(f"Real API test failed: {e}")
```

## Best Practices

### 1. Test Organization
- **One test file per client/module**
- **Descriptive test names** that explain the scenario
- **Group related tests** in test classes
- **Use appropriate markers** for test categorization

### 2. Mocking Strategy
- **Mock at the right level**: Instance methods, not class methods
- **Use AsyncMock for async methods**: Ensures `await` works correctly
- **Return realistic data**: Mock responses should match real API structure
- **Test error scenarios**: Mock exceptions and error responses

### 3. Assertions
- **Assert structure, not content**: For real API tests, verify data types and keys
- **Use meaningful assertions**: Check business logic, not implementation details
- **Test edge cases**: Empty responses, error conditions, boundary values

### 4. Performance
- **Keep tests fast**: Mocked tests should run in milliseconds
- **Minimize real API calls**: Use mocked tests for development
- **Parallel execution**: Use `pytest-xdist` for large test suites

### 5. Maintainability
- **DRY principle**: Use fixtures for common setup
- **Clear test data**: Use descriptive variable names and comments
- **Update tests with code changes**: Keep tests in sync with implementation

## Troubleshooting Tests

### Common Issues and Solutions

**1. "Module not found" errors**
```bash
# Ensure you're in the project root
cd /path/to/mcp-instana

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv sync
```

**2. "AsyncMock can't be used in 'await' expression"**
```python
# ❌ Problem: MagicMock interference
mock_client = MagicMock()
mock_client.method = AsyncMock(return_value=data)

# ✅ Solution: Use simple objects
mock_client = type('MockClient', (), {})()
mock_client.method = AsyncMock(return_value=data)
```

**3. "Tool not found" errors**
```python
# Ensure the tool name matches exactly
# Check the @register_as_tool decorator in the source code
# Verify the client is properly mocked
```

**4. Real API test failures**
```bash
# Check credentials
echo $INSTANA_API_TOKEN
echo $INSTANA_BASE_URL

# Test API connectivity
curl -H "Authorization: apiToken $INSTANA_API_TOKEN" "$INSTANA_BASE_URL/api/instana/version"
```

**5. Slow test execution**
```bash
# Run only mocked tests for development
uv run -m pytest tests/e2e/ -m mocked

# Use parallel execution
uv run -m pytest tests/e2e/ -m mocked -n auto
```

### Debug Commands

```bash
# Maximum verbosity
uv run -m pytest tests/e2e/ -m mocked -vvv -s

# Show test collection
uv run -m pytest tests/e2e/ --collect-only

# Run single test with debug
uv run -m pytest tests/e2e/test_file.py::TestClass::test_method -v -s

# Check test markers
uv run -m pytest tests/e2e/ --markers
```

### Test Coverage

```bash
# Generate coverage report
uv run -m pytest tests/e2e/ -m mocked --cov=src --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Generate coverage for specific modules
uv run -m pytest tests/e2e/ -m mocked --cov=src.client --cov-report=term
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      
      - name: Run mocked E2E tests
        run: |
          uv run -m pytest tests/e2e/ -m mocked --cov=src --cov-report=xml
      
      - name: Run real API tests (if credentials available)
        if: secrets.INSTANA_API_TOKEN
        env:
          INSTANA_API_TOKEN: ${{ secrets.INSTANA_API_TOKEN }}
          INSTANA_BASE_URL: ${{ secrets.INSTANA_BASE_URL }}
          RUN_REAL_API_TESTS: true
        run: |
          uv run -m pytest tests/e2e/ -m real_api --cov=src --cov-report=xml
```

## Test Metrics and Monitoring

### Key Metrics to Track
- **Test execution time**: Should be < 5 seconds for mocked tests
- **Test pass rate**: Should be > 95%
- **Coverage percentage**: Aim for > 80% code coverage
- **Flaky test rate**: Should be < 5%

### Monitoring Commands
```bash
# Test execution time
time uv run -m pytest tests/e2e/ -m mocked

# Coverage summary
uv run -m pytest tests/e2e/ -m mocked --cov=src --cov-report=term-missing

# Test statistics
uv run -m pytest tests/e2e/ -m mocked --tb=short -q
```

## Example Test Walkthrough

### Most Complex Test Case: `test_multiple_tool_execution_flow`

This test demonstrates:
- Multiple tool executions in sequence
- Proper async mocking
- MCP server integration testing
- Complex workflow validation

```python
@pytest.mark.asyncio
@pytest.mark.mocked
async def test_multiple_tool_execution_flow(self, instana_credentials):
    """Test a flow of multiple tool executions."""
    from src.mcp_server import execute_tool, MCPState
    mock_state = MCPState()
    
    # Create mock clients with proper method setup
    mock_app_resource_client = type('MockAppResourceClient', (), {})()
    mock_app_resource_client.get_applications = AsyncMock(return_value={
        "applications": [{"id": "app-1", "name": "Test App"}]
    })
    mock_app_resource_client.get_application_services = AsyncMock(return_value={
        "services": [{"id": "service-1", "name": "Test Service"}]
    })
    mock_state.app_resource_client = mock_app_resource_client
    
    mock_app_catalog_client = type('MockAppCatalogClient', (), {})()
    mock_app_catalog_client.get_application_metric_catalog = AsyncMock(return_value={
        "metrics": [{"id": "cpu_usage", "name": "CPU Usage"}]
    })
    mock_state.app_catalog_client = mock_app_catalog_client
    
    # Execute get_applications
    result1 = await execute_tool("get_applications", {}, mock_state)
    # Execute get_application_services
    result2 = await execute_tool("get_application_services", {"name_filter": "app-1"}, mock_state)
    # Execute get_application_metric_catalog
    result3 = await execute_tool("get_application_metric_catalog", {}, mock_state)
    
    assert "app-1" in result1
    assert "service-1" in result2
    assert "cpu_usage" in result3
```

### Key Learning Points:
1. **Mocking Strategy**: Use `type()` to create simple objects instead of `MagicMock` to avoid interference
2. **AsyncMock**: Essential for mocking async methods that use `await`
3. **Tool Dispatch**: The `execute_tool` function dynamically finds and calls the right method
4. **Workflow Testing**: Tests multiple tools in sequence to validate complete workflows

## Library Explanations

### Why Each Library?

| **Library** | **Purpose** | **Why Used** |
|-------------|-------------|--------------|
| **pytest** | Test runner | Industry standard, powerful fixtures, great plugins |
| **pytest-asyncio** | Async test support | Enables testing of async/await code |
| **unittest.mock.AsyncMock** | Async mocking | Mocks async methods so `await` works correctly |
| **type()** | Dynamic object creation | Creates clean mock objects without MagicMock interference |
| **Custom pytest markers** | Test categorization | Allows selective test execution and organization |

### Key Concepts:
- **Async Testing**: Required because our codebase uses async/await for I/O operations
- **Mocking Strategy**: Instance-level mocking avoids conflicts with FastMCP tool registration
- **Test Isolation**: Each test is independent and doesn't affect others
- **Performance**: Mocked tests run in milliseconds, enabling fast feedback loops

---

## Code Quality Checks

### Linting with Ruff

```bash
# Run ruff check on all files
uv run ruff check .

# Run ruff check with verbose output
uv run ruff check . -v

# Run ruff check with automatic fixes
uv run ruff check --fix .

# Run ruff check with unsafe fixes
uv run ruff check --fix --unsafe-fixes .
```

### Running Unit Tests

```bash
# Run all unit tests
uv run test

# Run all unit tests with verbose output
uv run test -v

# Run all unit tests with coverage
uv run test-coverage
```

## Quick Reference

### Most Common Commands
```bash
# Development workflow
uv run tests/e2e/run_e2e_tests.py mocked -v

# Before committing
uv run tests/e2e/run_e2e_tests.py all
uv run ruff check .
uv run test -v

# Debug a specific test
uv run -m pytest tests/e2e/test_file.py::TestClass::test_method -v -s

# Generate coverage
uv run tests/e2e/run_e2e_tests.py mocked -c
uv run test-coverage
```

### Environment Setup Checklist
- [ ] Virtual environment activated
- [ ] Dependencies installed (`uv sync`)
- [ ] Pytest working (`uv run -m pytest --version`)
- [ ] For real API tests: credentials set in environment variables