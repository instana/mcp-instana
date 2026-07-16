#!/usr/bin/env python3
"""
Unified test runner script with coverage for mcp-instana

This script runs all tests (both synchronous and asynchronous) with coverage analysis.
"""

import argparse
import os
import subprocess
import sys
from typing import List, Optional


def run_all_tests_with_coverage(
    test_path: Optional[str] = None,
    verbose: bool = False,
    report_type: str = 'report',
    include_patterns: Optional[List[str]] = None,
    omit_patterns: Optional[List[str]] = None
) -> bool:
    """
    Run all tests with coverage

    Args:
        test_path: Optional path to specific test module, file, or directory
        verbose: Whether to run tests in verbose mode
        report_type: Type of report to generate ('report', 'html', or 'xml')
        include_patterns: List of file patterns to include in coverage
        omit_patterns: List of file patterns to omit from coverage

    Returns:
        True if all tests pass, False otherwise
    """
    # Add the project root to the Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    # Run coverage in the subprocess so pytest execution is actually measured.
    pytest_targets = [
        "tests/application",
        "tests/automation",
        "tests/core",
        "tests/custom_dashboard",
        "tests/event",
        "tests/infrastructure",
        "tests/log",
        "tests/mobile_app",
        "tests/prompts",
        "tests/releases",
        "tests/router",
        "tests/slo",
        "tests/website",
    ]

    coverage_command = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        "--source=src",
    ]

    for pattern in omit_patterns or []:
        coverage_command.append(f"--omit={pattern}")

    coverage_command.extend(["-m", "pytest"])

    if test_path:
        coverage_command.append(test_path)
    else:
        coverage_command.extend(pytest_targets)

    if verbose:
        coverage_command.append("-v")

    completed = subprocess.run(coverage_command, check=False)
    success = completed.returncode == 0

    if report_type == 'html':
        report_command = [sys.executable, "-m", "coverage", "html"]
        print("HTML report generated in htmlcov directory")
    elif report_type == 'xml':
        report_command = [sys.executable, "-m", "coverage", "xml"]
        print("XML report generated: coverage.xml")
    else:
        report_command = [sys.executable, "-m", "coverage", "report"]

    for pattern in omit_patterns or []:
        report_command.append(f"--omit={pattern}")

    subprocess.run(report_command, check=False)

    return success

def main():
    parser = argparse.ArgumentParser(description='Run all tests with coverage for mcp-instana')
    parser.add_argument('test_path', nargs='?', help='Path to specific test module, file, or directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Run tests in verbose mode')
    parser.add_argument('--html', action='store_const', dest='report', const='html',
                        help='Generate HTML coverage report')
    parser.add_argument('--xml', action='store_const', dest='report', const='xml',
                        help='Generate XML coverage report')
    parser.add_argument('--include', action='append', help='File patterns to include in coverage (can be used multiple times)')
    parser.add_argument('--omit', action='append', help='File patterns to omit from coverage (can be used multiple times)')

    args = parser.parse_args()

    # Default include pattern to focus on all source code, including nested packages
    include_patterns = args.include if args.include else ["src/*", "src/**/*.py"]

    # Default omit pattern to exclude tests and other non-source files
    omit_patterns = args.omit if args.omit else ["tests/*", "setup.py"]

    success = run_all_tests_with_coverage(
        args.test_path,
        args.verbose,
        getattr(args, 'report', 'report'),
        include_patterns,
        omit_patterns
    )

    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()


