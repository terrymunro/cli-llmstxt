#!/usr/bin/env python3
"""
Test script for GitIgnore functionality.

This script creates a test repository with .gitignore files and tests
the gitignore handler functionality.
"""

import os
import tempfile
import shutil
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llmstxt.gitignore_handler import GitIgnoreHandler


def create_test_repo():
    """Create a test repository with .gitignore files."""
    # Create temporary directory
    test_dir = tempfile.mkdtemp(prefix="gitignore_test_")
    test_path = Path(test_dir)

    # Create .gitignore in root
    gitignore_content = """
# Python files
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Temporary files
tmp/
temp/
*.tmp
"""

    (test_path / ".gitignore").write_text(gitignore_content.strip())

    # Create subdirectory with its own .gitignore
    subdir = test_path / "subproject"
    subdir.mkdir()
    subdir_gitignore = """
# Subproject specific ignores
local_config.json
debug/
*.debug
"""
    (subdir / ".gitignore").write_text(subdir_gitignore.strip())

    # Create test files
    files_to_create = [
        "main.py",
        "config.py",
        "__pycache__/cache.pyc",
        "build/output.txt",
        "README.md",
        ".vscode/settings.json",
        "data.log",
        "temp/file.tmp",
        "subproject/app.py",
        "subproject/local_config.json",
        "subproject/debug/info.txt",
        "subproject/test.debug",
        "subproject/normal.py",
    ]

    for file_path in files_to_create:
        full_path = test_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(f"Content of {file_path}")

    return str(test_path)


def test_gitignore_handler():
    """Test the GitIgnore handler functionality."""
    print("Creating test repository...")
    repo_path = create_test_repo()

    try:
        print(f"Test repository created at: {repo_path}")

        # Initialize GitIgnore handler
        print("\nInitializing GitIgnore handler...")
        handler = GitIgnoreHandler(repo_path)

        # Get statistics
        stats = handler.get_stats()
        print("GitIgnore handler statistics:")
        print(f"  Total patterns: {stats['total_patterns']}")
        print(f"  Regular patterns: {stats['regular_patterns']}")
        print(f"  Negation patterns: {stats['negation_patterns']}")
        print(f"  GitIgnore files found: {stats['gitignore_files_found']}")

        # Test files
        test_files = [
            "main.py",  # Should NOT be ignored
            "config.py",  # Should NOT be ignored
            "__pycache__/cache.pyc",  # Should be ignored
            "build/output.txt",  # Should be ignored
            "README.md",  # Should NOT be ignored
            ".vscode/settings.json",  # Should be ignored
            "data.log",  # Should be ignored
            "temp/file.tmp",  # Should be ignored
            "subproject/app.py",  # Should NOT be ignored
            "subproject/local_config.json",  # Should be ignored (subproject gitignore)
            "subproject/debug/info.txt",  # Should be ignored (subproject gitignore)
            "subproject/test.debug",  # Should be ignored (subproject gitignore)
            "subproject/normal.py",  # Should NOT be ignored
        ]

        print("\nTesting file ignore status:")
        for file_path in test_files:
            full_path = os.path.join(repo_path, file_path)
            should_ignore = handler.should_ignore(full_path)
            status = "IGNORED" if should_ignore else "NOT IGNORED"
            print(f"  {file_path:<30} -> {status}")

        # Test get_ignore_patterns_for_exclusions
        patterns = handler.get_ignore_patterns_for_exclusions()
        print(f"\nGenerated exclusion patterns ({len(patterns)} total):")
        for pattern in patterns[:10]:  # Show first 10
            print(f"  {pattern}")
        if len(patterns) > 10:
            print(f"  ... and {len(patterns) - 10} more")

        print("\nTest completed successfully!")

    finally:
        # Clean up
        print("\nCleaning up test repository...")
        shutil.rmtree(repo_path)
        print("Cleanup completed.")


if __name__ == "__main__":
    test_gitignore_handler()
