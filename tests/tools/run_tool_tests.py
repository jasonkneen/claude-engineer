#!/usr/bin/env python3
import os
import sys
import unittest
import argparse
from pathlib import Path


def setup_environment():
    """Set up the environment for testing"""
    # Add project root to PYTHONPATH
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Print environment info
    print(f"Python version: {sys.version}")
    print(f"Project root: {project_root}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")
    print("-" * 80)


def run_tests(pattern=None, verbose=False):
    """Run the tool tests"""
    # Get the directory containing this script
    test_dir = Path(__file__).parent

    # Create test loader
    loader = unittest.TestLoader()

    # Discover and load tests
    if pattern:
        print(f"Running tests matching pattern: {pattern}")
        suite = loader.discover(start_dir=test_dir, pattern=pattern)
    else:
        print("Running all tool tests")
        suite = loader.discover(start_dir=test_dir, pattern="test_*.py")

    # Create test runner
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)

    # Run tests
    result = runner.run(suite)

    # Return 0 if tests passed, 1 if any failed
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run tool tests")
    parser.add_argument(
        "--pattern", help="Test file pattern to run (e.g., test_error_handler.py)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    setup_environment()
    sys.exit(run_tests(args.pattern, args.verbose))
