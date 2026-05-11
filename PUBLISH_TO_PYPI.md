# Publishing mcp-instana to PyPI

This guide documents the process for publishing new versions of the `mcp-instana` package to PyPI.

## Prerequisites

- Access to PyPI account with publishing rights for `mcp-instana`
- PyPI API token (stored securely)
- `uv` package manager installed
- `twine` installed for uploading to PyPI

## Version Update Process

### 1. Update Version Numbers

Update the version in three locations:

**pyproject.toml** (line 7):
```toml
version = "0.9.7"
```

**src/core/utils.py** (line 35):
```python
__version__ = "0.9.7"
```

**tests/core/test_utils.py** (line 1075):
```python
self.assertEqual(src.core.utils.__version__, "0.9.7")
```

### 2. Update CHANGELOG.md

Add a new entry at the top of the changelog:

```markdown
### 0.9.7
-  **Maintenance:** Version bump for PyPI release with schema files intact.
```

### 3. Clean Build Artifacts

Remove any existing build artifacts:

```bash
rm -rf dist/ build/ *.egg-info
```

### 4. Build Distribution Packages

Use `uv` to build both source distribution and wheel:

```bash
uv build
```

This creates:
- `dist/mcp_instana-0.9.7.tar.gz` (source distribution)
- `dist/mcp_instana-0.9.7-py3-none-any.whl` (wheel)

### 5. Verify Schema Files

**CRITICAL**: Verify that all 7 schema files are included in the wheel:

```bash
unzip -l dist/mcp_instana-0.9.7-py3-none-any.whl | grep schema
```

Expected output should show all 7 schema files:
```
schema/db2Database_schema.json
schema/host_schema.json
schema/ibmMqQueue_schema.json
schema/jvmRuntimePlatform_schema.json
schema/kubernetesDeployment_schema.json
schema/kubernetesPod_schema.json
schema/oTelLLM_schema.json
```

### 6. Upload to PyPI

Upload the distribution packages using twine:

```bash
twine upload dist/mcp_instana-0.9.7*
```

You will be prompted for:
- Username: `__token__`
- Password: Your PyPI API token

### 7. Verify Publication

After successful upload, verify the package at:
```
https://pypi.org/project/mcp-instana/0.9.7/
```

## Complete Command Sequence

Here's the complete sequence of commands for publishing a new version:

```bash
# 1. Update version in files (manual step)
# - pyproject.toml
# - src/core/utils.py
# - tests/core/test_utils.py
# - CHANGELOG.md

# 2. Clean build artifacts
rm -rf dist/ build/ *.egg-info

# 3. Build distribution packages
uv build

# 4. Verify schema files are included
unzip -l dist/mcp_instana-0.9.7-py3-none-any.whl | grep schema

# 5. Upload to PyPI
twine upload dist/mcp_instana-0.9.7*
```

## Troubleshooting

### Build Module Not Found

If you get "No module named build", install it:
```bash
pip install build
```

Or use `uv` which has build capabilities built-in.

### Schema Files Missing

If schema files are not included in the wheel:
1. Check `pyproject.toml` for the `[tool.hatchling.build.targets.wheel]` section
2. Ensure the schema directory is properly configured in the build system
3. Verify the schema files exist in the `schema/` directory

### Authentication Failed

If twine authentication fails:
1. Verify your PyPI API token is correct
2. Use `__token__` as the username (not your PyPI username)
3. Ensure the token has the correct permissions for the package

## Version History

- **0.9.7**: Maintenance release with schema files intact
- **0.9.6**: Fixed ClientSamplingHandler import error
- **0.9.5**: Introduced unified smart router for releases operations
- **0.9.0**: Introduced unified smart router for SLO operations

## Notes

- Always verify schema files are included before uploading
- Test the package locally before publishing
- Keep the CHANGELOG.md updated with each release
- Version numbers follow semantic versioning (MAJOR.MINOR.PATCH)