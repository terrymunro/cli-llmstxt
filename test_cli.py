#!/usr/bin/env python3
"""
Test CLI options for gitignore functionality.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llmstxt.cli import parse_arguments


def test_cli_options():
    """Test the CLI options include gitignore support."""

    # Test help output
    try:
        # This will show help and exit
        sys.argv = ["test", "--help"]
        parse_arguments()
    except SystemExit:
        pass

    # Test with gitignore options
    sys.argv = ["test", "/some/repo", "--ignore_gitignore"]
    args = parse_arguments()
    print("Testing --ignore_gitignore option:")
    print(f"  ignore_gitignore: {getattr(args, 'ignore_gitignore', 'NOT FOUND')}")
    print(f"  respect_gitignore: {getattr(args, 'respect_gitignore', 'NOT FOUND')}")

    # Test default behavior
    sys.argv = ["test", "/some/repo"]
    args = parse_arguments()
    print("\nTesting default behavior:")
    print(f"  ignore_gitignore: {getattr(args, 'ignore_gitignore', 'NOT FOUND')}")
    print(f"  respect_gitignore: {getattr(args, 'respect_gitignore', 'NOT FOUND')}")


if __name__ == "__main__":
    test_cli_options()
