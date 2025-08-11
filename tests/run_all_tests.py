#!/usr/bin/env python3
"""
Unified test runner script for mcp-instana

This script runs all tests (both synchronous and asynchronous) in the project.
"""

import argparse
import asyncio
import importlib.util
import os
import sys
import unittest
from typing import Dict, List, Optional, Set, Tuple, Type


def import_module_from_path(path: str):
    """Import a module from a file path"""
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Make sure the path is absolute
    abs_path = os.path.abspath(path)

    # Get the path relative to the project root
    if abs_path.startswith(project_root):
        rel_to_root = os.path.relpath(abs_path, project_root)
    else:
        # If the path is not under the project root, use just the filename
        rel_to_root = os.path.basename(abs_path)

    # Convert to module name using the same convention as unittest
    module_name = os.path.splitext(rel_to_root)[0].replace(os.path.sep, '.')

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not import module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def discover_test_modules(start_dir: str) -> List[str]:
    """
    Discover all test modules in the given directory

    Args:
        start_dir: Directory to start discovery from

    Returns:
        List of paths to test modules
    """
    test_files = []

    for root, _, files in os.walk(start_dir):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                test_files.append(os.path.join(root, file))

    return test_files

def is_async_test_module(module) -> bool:
    """
    Check if a module contains async tests

    Args:
        module: The module to check

    Returns:
        True if the module contains async tests, False otherwise
    """
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj != unittest.TestCase:
            for method_name in dir(obj):
                if method_name.startswith('test_'):
                    method = getattr(obj, method_name)
                    if asyncio.iscoroutinefunction(method):
                        return True
    return False

def get_test_classes(module) -> List[Type[unittest.TestCase]]:
    """
    Get all test classes from a module

    Args:
        module: The module to get test classes from

    Returns:
        List of test classes
    """
    test_classes = []
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj != unittest.TestCase:
            test_classes.append(obj)
    return test_classes

def run_sync_tests(test_path: Optional[str] = None, verbose: bool = False) -> Tuple[bool, Dict[str, Set[str]]]:
    """
    Run synchronous tests using unittest

    Args:
        test_path: Optional path to specific test module, file, or directory
        verbose: Whether to run tests in verbose mode

    Returns:
        True if all tests pass, False otherwise
    """
    # Set up the test loader
    loader = unittest.TestLoader()

    # Determine what tests to run
    if test_path:
        # Convert path to module name if it's a file
        if test_path.endswith('.py'):
            # Use import_module_from_path to handle full paths correctly
            module = import_module_from_path(test_path)
            suite = loader.loadTestsFromModule(module)
        else:
            # If it's a directory, discover tests in that directory
            suite = loader.discover(test_path)
    else:
        # Run all tests in the tests directory
        suite = loader.discover('tests')

    # Run the tests
    verbosity = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    # Collect failed tests
    failed_tests = {}
    for test in result.failures + result.errors:
        test_case = test[0]
        test_method = test_case._testMethodName
        test_class = test_case.__class__.__name__
        test_module = test_case.__class__.__module__

        if test_module not in failed_tests:
            failed_tests[test_module] = set()
        failed_tests[test_module].add(f"{test_class}.{test_method}")

    # Return True if all tests pass, False otherwise, along with failed tests
    return result.wasSuccessful(), failed_tests

def run_async_test_module(module, verbose: bool = False) -> Tuple[bool, int, Dict[str, Set[str]]]:
    """
    Run async tests from a module

    Args:
        module: The module containing async tests
        verbose: Whether to run tests in verbose mode

    Returns:
        Tuple of (success, test_count) where:
          - success: True if all tests pass, False otherwise
          - test_count: Number of tests run
    """
    # Find all test classes
    test_classes = get_test_classes(module)

    # Run all tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    all_passed = True
    test_count = 0
    failed_tests = {}
    module_name = module.__name__

    for test_class in test_classes:
        if verbose:
            print(f"Running tests for {test_class.__name__}")

        for name in dir(test_class):
            if name.startswith('test_'):
                test_instance = test_class()
                # Call setUp
                if hasattr(test_instance, 'setUp'):
                    test_instance.setUp()

                try:
                    # Run the test
                    test_method = getattr(test_instance, name)
                    if asyncio.iscoroutinefunction(test_method):
                        if verbose:
                            print(f"  Running async test: {name}")
                        loop.run_until_complete(test_method())
                    else:
                        if verbose:
                            print(f"  Running sync test: {name}")
                        test_method()
                    test_count += 1
                except Exception as e:
                    print(f"Error in {test_class.__name__}.{name}: {e}")
                    all_passed = False
                    test_count += 1

                    # Track failed test
                    if module_name not in failed_tests:
                        failed_tests[module_name] = set()
                    failed_tests[module_name].add(f"{test_class.__name__}.{name}")
                finally:
                    # Call tearDown
                    if hasattr(test_instance, 'tearDown'):
                        test_instance.tearDown()

    return all_passed, test_count, failed_tests

def run_all_tests(test_path: Optional[str] = None, verbose: bool = False) -> bool:
    """
    Run all tests (both sync and async)

    Args:
        test_path: Optional path to specific test module, file, or directory
        verbose: Whether to run tests in verbose mode

    Returns:
        True if all tests pass, False otherwise
    """
    import time
    import unittest  # Import unittest here to ensure it's available in this scope
    start_time = time.time()

    # Add the project root to the Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    total_tests = 0
    all_failed_tests = {}

    # If a specific test path is provided, handle it
    if test_path:
        if os.path.isfile(test_path):
            # Single file case
            module = import_module_from_path(test_path)
            if is_async_test_module(module):
                success, test_count, failed_tests = run_async_test_module(module, verbose)
                all_failed_tests.update(failed_tests)
                total_tests += test_count
                elapsed_time = time.time() - start_time
                print(f"\nRan {test_count} tests in {elapsed_time:.3f}s")

                # Print failed tests
                if failed_tests:
                    print("\nFailed tests:")
                    for module_name, tests in failed_tests.items():
                        for test in tests:
                            print(f"  {module_name}: {test}")

                return success
            else:
                # For sync tests, unittest will print the summary
                success, failed_tests = run_sync_tests(test_path, verbose)
                all_failed_tests.update(failed_tests)

                # Print failed tests
                if failed_tests:
                    print("\nFailed tests:")
                    for module_name, tests in failed_tests.items():
                        for test in tests:
                            print(f"  {module_name}: {test}")

                return success
        else:
            # Directory case - use unittest for discovery
            success, failed_tests = run_sync_tests(test_path, verbose)
            all_failed_tests.update(failed_tests)

            # Print failed tests
            if failed_tests:
                print("\nFailed tests:")
                for module_name, tests in failed_tests.items():
                    for test in tests:
                        print(f"  {module_name}: {test}")

            return success

    # No specific path - run all tests
    # Use a custom approach to avoid import issues
    if test_path is None:
        # Manually import and run all test modules to avoid discovery issues
        test_modules = [
            'tests.application.test_application_alert_config',
            'tests.application.test_application_analyze',
            'tests.application.test_application_catalog',
            'tests.application.test_application_metrics',
            'tests.application.test_application_resources',
            'tests.application.test_application_topology',
            'tests.core.test_server',
            'tests.core.test_utils',
            'tests.event.test_events_tools',
            'tests.infrastructure.test_infrastructure_analyze',
            'tests.infrastructure.test_infrastructure_catalog',
            'tests.infrastructure.test_infrastructure_metrics',
            'tests.infrastructure.test_infrastructure_resources',
            'tests.infrastructure.test_infrastructure_topology',
            'tests.log.test_log_alert_configuration',
            'tests.prompts.test_mcp_prompts'
        ]

        all_tests = unittest.TestSuite()
        verbosity = 2 if verbose else 1
        runner = unittest.TextTestRunner(verbosity=verbosity)

        for module_name in test_modules:
            try:
                module = importlib.import_module(module_name)
                suite = unittest.defaultTestLoader.loadTestsFromModule(module)
                all_tests.addTest(suite)
            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")

        result = runner.run(all_tests)

        # Collect failed tests
        sync_failed_tests = {}
        for test in result.failures + result.errors:
            test_case = test[0]
            test_method = test_case._testMethodName
            test_class = test_case.__class__.__name__
            test_module = test_case.__class__.__module__

            if test_module not in sync_failed_tests:
                sync_failed_tests[test_module] = set()
            sync_failed_tests[test_module].add(f"{test_class}.{test_method}")

        sync_result = result.wasSuccessful()
        all_failed_tests.update(sync_failed_tests)
    else:
        # For specific paths, use the normal run_sync_tests function
        sync_result, sync_failed_tests = run_sync_tests(test_path, verbose)
        all_failed_tests.update(sync_failed_tests)

    # Keep track of which modules have already been tested by unittest
    # Extract module names from the failed tests dictionary keys
    tested_modules = set()
    for module_name in sync_failed_tests:
        # Get the base module name without the package prefix
        base_name = module_name.split('.')[-1]
        tested_modules.add(base_name)

    # Then check if we have any async tests that need special handling
    test_modules = discover_test_modules(os.path.join(project_root, 'tests'))
    async_results = []
    async_test_count = 0

    for module_path in test_modules:
        module = import_module_from_path(module_path)
        # Skip modules that have already been tested by unittest
        module_name = module.__name__
        base_name = module_name.split('.')[-1]

        if base_name in tested_modules:
            if verbose:
                print(f"Skipping {module_path} as it was already tested by unittest")
            continue

        if is_async_test_module(module):
            if verbose:
                print(f"\nRunning async tests in {module_path}")
            success, test_count, failed_tests = run_async_test_module(module, verbose)
            all_failed_tests.update(failed_tests)
            async_results.append(success)
            async_test_count += test_count

    # Calculate total tests run
    # For sync tests, we need to estimate the count from the unittest result
    # This is a bit of a hack, but unittest doesn't expose the test count directly
    loader = unittest.TestLoader()
    suite = loader.discover('tests')
    total_test_count = suite.countTestCases()

    # We don't want to double-count the async tests that were already counted in the sync suite
    # So we use the total count from the test discovery, which includes all tests
    total_tests = total_test_count
    elapsed_time = time.time() - start_time

    # Print summary
    print(f"\nRan {total_tests} tests in {elapsed_time:.3f}s")

    if sync_result and all(async_results):
        print("\n✅ All Tests OK")
    else:
        # Count total failed tests
        total_failed = sum(len(tests) for tests in all_failed_tests.values())

        print(f"\n❌ {total_failed} test(s) failed.")

        # Print all failed tests with better formatting
        if all_failed_tests:
            print("\n=== FAILED TESTS ===")

            # Normalize module names to prevent duplicates
            normalized_failures = {}
            for module_name, tests in all_failed_tests.items():
                # Extract the base module name (without package prefix)
                base_name = module_name.split('.')[-1]

                # Use the base name as the key
                if base_name not in normalized_failures:
                    normalized_failures[base_name] = set()
                normalized_failures[base_name].update(tests)

            # Print the normalized failures
            for module_name, tests in sorted(normalized_failures.items()):
                print(f"\n📁 {module_name}")
                for test in sorted(tests):
                    print(f"  ↳ {test}")
            print("\n===================")

    # Tests pass only if all sync and async tests pass
    return sync_result and all(async_results)

def main():
    parser = argparse.ArgumentParser(description='Run all tests for mcp-instana')
    parser.add_argument('test_path', nargs='?', help='Path to specific test module, file, or directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Run tests in verbose mode')

    args = parser.parse_args()

    success = run_all_tests(args.test_path, args.verbose)

    # Exit with appropriate status code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()


