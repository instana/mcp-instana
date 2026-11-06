<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Contributing to MCP-Instana](#contributing-to-mcp-instana)
- [Prerequisites](#prerequisites)
- [Steps to Build a New MCP Tool](#steps-to-build-a-new-mcp-tool)
  - [1. Fork this repo](#1-fork-this-repo)
  - [2. Set Up Your Development Environment](#2-set-up-your-development-environment)
  - [3. Create a New MCP Tools Module](#3-create-a-new-mcp-tools-module)
  - [4. Implement the MCP Tools class](#4-implement-the-mcp-tools-class)
  - [5. Write API tool Description precisely](#5-write-api-tool-description-precisely)
  - [6. Update the Main Server File](#6-update-the-main-server-file)
  - [7. Test Your MCP Tool](#7-test-your-mcp-tool)
  - [8. Add Documentation](#8-add-documentation)
  - [9. Code Linting](#9-code-linting)
  - [Troubleshooting](#troubleshooting)
  - [Getting Help](#getting-help)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

### Contributing to MCP-Instana

This guide provides step-by-step instructions for building a new MCP (Model Context Protocol) tool for the [Instana API](https://developer.ibm.com/apis/catalog/instana--instana-rest-api/Introduction) within the mcp-instana project.

### Prerequisites

- Python 3.11 or higher
- Access to Instana API (API token and base URL)
- Access to Instana python SDK [git+https://github.ibm.com/instana/instana-python-sdk](https://github.ibm.com/instana/instana-python-sdk)
- Basic understanding of the [Instana API endpoints](https://developer.ibm.com/apis/catalog/instana--instana-rest-api/Introduction)
- Familiarity with Python async programming

### Steps to Build a New MCP Tool

#### 1. Fork this repo

To begin development, you’ll need your own copy of the repository:

- Go to the GitHub page of this repository.
- Click the Fork button in the top-right corner.
- Select your personal GitHub account (or your organization’s account) as the destination.
- GitHub will create a forked copy of the repository under your account, e.g. https://github.com/<Your GitHub Username>/mcp-instana

#### 2. Set Up Your Development Environment

```bash
# Clone the repository
git clone https://github.com/<Your GitHub Username>/mcp-instana.git
cd mcp-instana

# Set up the environment
uv sync

# Alternative: Install from PyPI
pip install mcp-instana
```

#### 3. Create a New MCP Tools Module

Create a new file in the src/client directory with a descriptive name following the pattern: <api_name>_mcp_tools.py

#### 4. Implement the MCP Tools class

Follow any existing tools class under src/client to know the template structure for your new class.

#### 5. Write API tool Description precisely

For each tool, provide a clear description as per the prompt engineering guidelines that helps the LLM understand when to use this tool:
 

 ```bash

 @register_as_tool
async def get_example_data(self, query: str, ctx=None) -> Dict[str, Any]:
    """
    Retrieve example data from Instana based on the provided query.
    
    This tool is useful when you need to get information about [specific use case].
    You can filter by [parameters] to narrow down results. Use this when you want
    to [common user intent], understand [specific information], or analyze [metrics/data].
    
    For example, use this tool when asked about '[example query 1]', '[example query 2]',
    or when someone wants to '[example intent]'.
    
    Args:
        query: Query string to filter results
        ctx: The MCP context (optional)
        
    Returns:
        Dictionary containing example data or error information
    """
 ```


#### 6. Update the Main Server File

Update src/core/server.py to register your new tools:

#### 7. Test Your MCP Tool

Build the mcp-instana with:

```bash
# For development (editable install)
uv pip install -e .

# Or install from PyPI
pip install mcp-instana
```

Now open/restart the mcp host like Claude Desktop/GitHub Copilot and then run the query to test your new tool.

To run the MCP server locally:

**Using Development Installation:**
```bash
# Run in Streamable HTTP mode
uv run src/core/server.py --transport streamable-http --debug

# Run with specific tool categories
uv run src/core/server.py --tools app,infra --transport streamable-http

# List all available tool categories
uv run src/core/server.py --list-tools
```

**Using CLI (PyPI Installation):**
```bash
# Run in Streamable HTTP mode
mcp-instana --transport streamable-http --debug

# Run with specific tool categories
mcp-instana --tools app,infra --transport streamable-http

# List all available tool categories
mcp-instana --list-tools
```

#### 8. Add Documentation
Update the README.md file to include your new tool in the tools table:

```bash

| Tool                      | Category          | Description                              |
|---------------------------|-------------------|------------------------------------------|
| `[method_name]`           | [API Category]    | [Brief description of what the tool does]|
```

#### 9. Code Linting

This project uses [Ruff](https://github.com/astral-sh/ruff) for code linting. Ruff is a fast Python linter written in Rust that helps maintain code quality and consistency.

The project ignores several linting rules to accommodate the existing codebase. See the `ignore` list in `pyproject.toml` for the complete list of ignored rules, which includes:

- `E501`: Line too long
- `SIM117`: Use a single `with` statement with multiple contexts
- `PLR0912`: Too many branches
- `E402`: Module level import not at top of file
- `ARG001`, `ARG002`, `ARG005`: Unused function/method/lambda arguments
- `PLR2004`: Magic value comparison
- `PLR0915`: Too many statements
- `PLR0911`: Too many return statements
- `B904`: Within an except clause, raise exceptions with raise from
- And others as needed for the codebase

To run the linter locally:

```bash
# Run linter to check for issues
./run_ruff_check.sh

# Run linter and automatically fix issues
./run_ruff_check.sh --fix

# Run linter and automatically fix issues (including unsafe fixes)
./run_ruff_check.sh --fix --unsafe-fixes
```

The project also includes CI integration via GitHub Actions that automatically runs linting checks on all pull requests and pushes to the main branch. The workflow configuration is located in `.github/workflows/lint.yml`.

For pull requests, the CI will:
1. Check for linting issues
2. Automatically fix safe linting issues
3. Commit the fixes back to your branch

Before submitting your code, make sure to run the linter and fix any issues. Many common issues can be automatically fixed using the `--fix` option. The CI pipeline will also verify that your code passes all linting checks.

#### Troubleshooting

If you encounter import errors, check that you're using the correct import paths.
If API calls fail, verify your API token and base URL.
Use debug printing to trace the execution flow and identify issues.
Check the Instana API documentation for any specific requirements or limitations.

#### Getting Help

If you need assistance, please open an issue on the GitHub repository or contact the project maintainers.
