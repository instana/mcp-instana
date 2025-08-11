#!/usr/bin/env python
"""
E2E Test Runner for MCP Instana Internal

This script provides convenient ways to run different types of e2e tests.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_tests(test_type: str, verbose: bool = False, coverage: bool = False):
    """Run e2e tests based on the specified type."""

    # Base pytest command
    cmd = ["uv", "run", "-m", "pytest"]

    # Add test directory
    cmd.append("tests/e2e/")

    # Add markers based on test type
    if test_type == "mocked":
        cmd.extend(["-m", "mocked"])
        print("Running mocked E2E tests...")
    elif test_type == "real":
        cmd.extend(["-m", "real_api"])
        print("Running real API E2E tests...")
    elif test_type == "all":
        print("Running all E2E tests...")
    else:
        print(f"Unknown test type: {test_type}")
        return False

    # Add verbosity
    if verbose:
        cmd.append("-v")

    # Add coverage if requested
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])

    # Add additional options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])

    # Run the tests
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Tests failed with exit code: {e.returncode}")
        return False


def check_environment():
    """Check if the test environment is properly set up."""

    # Check if we're in the right directory
    if not Path("src").exists():
        print("Error: 'src' directory not found. Please run from the project root.")
        return False

    # Check if e2e test directory exists
    if not Path("tests/e2e").exists():
        print("Error: 'tests/e2e' directory not found.")
        return False

    # Check for required environment variables for real API tests
    if os.environ.get("RUN_REAL_API_TESTS", "false").lower() == "true":
        required_vars = ["INSTANA_API_TOKEN", "INSTANA_BASE_URL"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]

        if missing_vars:
            print(f"Warning: Missing environment variables for real API tests: {missing_vars}")
            print("Real API tests will be skipped.")

    return True


def main():
    """Main function to parse arguments and run tests."""

    parser = argparse.ArgumentParser(description="Run E2E tests for MCP Instana Internal")
    parser.add_argument(
        "test_type",
        choices=["mocked", "real", "all"],
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Run tests in verbose mode"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--list-tests",
        action="store_true",
        help="List available tests without running them"
    )

    args = parser.parse_args()

    # Check environment
    if not check_environment():
        sys.exit(1)

    # List tests if requested
    if args.list_tests:
        cmd = ["uv", "run", "-m", "pytest", "tests/e2e/", "--collect-only", "-q"]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError:
            print("Failed to list tests")
            sys.exit(1)
        return

    # Run tests
    success = run_tests(args.test_type, args.verbose, args.coverage)

    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
