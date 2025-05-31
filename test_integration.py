#!/usr/bin/env python3
"""
Full integration test for GitIgnore functionality.

This script tests the entire pipeline with gitignore support.
"""

import os
import tempfile
import shutil
from pathlib import Path
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from llmstxt.gitignore_handler import GitIgnoreHandler
from llmstxt.custom_file_reader import CustomFileReader


def create_test_repo():
    """Create a test repository with .gitignore files and various file types."""
    # Create temporary directory
    test_dir = tempfile.mkdtemp(prefix="integration_test_")
    test_path = Path(test_dir)

    # Create .gitignore in root
    gitignore_content = """
# Build artifacts
build/
dist/
*.egg-info/

# Cache files
__pycache__/
*.pyc
.cache/

# IDE files
.vscode/
.idea/

# Logs
*.log

# Test artifacts
.pytest_cache/
"""

    (test_path / ".gitignore").write_text(gitignore_content.strip())

    # Create test files
    files_to_create = [
        ("main.py", "#!/usr/bin/env python3\nprint('Hello, World!')"),
        ("utils.py", "def helper_function():\n    pass"),
        ("README.md", "# Test Project\n\nThis is a test project."),
        ("build/output.exe", "binary content"),
        ("__pycache__/main.cpython-39.pyc", "binary cache"),
        (".vscode/settings.json", '{"python.defaultInterpreter": "python3"}'),
        ("app.log", "2024-01-01 10:00:00 INFO Application started"),
        ("requirements.txt", "requests==2.28.0\nflask==2.0.1"),
        (
            "test_app.py",
            "import unittest\n\nclass TestApp(unittest.TestCase):\n    pass",
        ),
    ]

    for file_path, content in files_to_create:
        full_path = test_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    return str(test_path)


def test_integration():
    """Test the full integration of gitignore support."""
    print("Creating test repository...")
    repo_path = create_test_repo()

    try:
        print(f"Test repository created at: {repo_path}")

        # Test 1: GitIgnore handler alone
        print("\n=== Test 1: GitIgnore Handler ===")
        handler = GitIgnoreHandler(repo_path)
        stats = handler.get_stats()
        print(f"Patterns loaded: {stats['total_patterns']}")

        # Test file filtering
        test_files = [
            "main.py",
            "utils.py",
            "README.md",
            "build/output.exe",
            "__pycache__/main.cpython-39.pyc",
            ".vscode/settings.json",
            "app.log",
            "requirements.txt",
            "test_app.py",
        ]

        print("File ignore status:")
        for file_path in test_files:
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                should_ignore = handler.should_ignore(full_path)
                status = "IGNORED" if should_ignore else "INCLUDED"
                print(f"  {file_path:<30} -> {status}")

        # Test 2: Custom File Reader with GitIgnore
        print("\n=== Test 2: Custom File Reader with GitIgnore ===")
        reader = CustomFileReader()
        extensions = [".py", ".md", ".txt", ".log", ".json", ".exe"]
        exclusions = ["**/temp/**"]  # Basic exclusions only

        # Load without gitignore
        print("\nWithout GitIgnore support:")
        docs_without_gitignore = reader.load_data(
            repo_path=repo_path,
            extensions=extensions,
            exclusions=exclusions,
            gitignore_handler=None,
        )
        print(f"Files loaded: {len(docs_without_gitignore)}")
        for doc in docs_without_gitignore:
            file_path = doc.metadata.get("file_path", "")
            rel_path = os.path.relpath(file_path, repo_path)
            print(f"  {rel_path}")

        # Load with gitignore
        print("\nWith GitIgnore support:")
        docs_with_gitignore = reader.load_data(
            repo_path=repo_path,
            extensions=extensions,
            exclusions=exclusions,
            gitignore_handler=handler,
        )
        print(f"Files loaded: {len(docs_with_gitignore)}")
        for doc in docs_with_gitignore:
            file_path = doc.metadata.get("file_path", "")
            rel_path = os.path.relpath(file_path, repo_path)
            print(f"  {rel_path}")

        # Summary
        print("\n=== Summary ===")
        print(f"Files without gitignore: {len(docs_without_gitignore)}")
        print(f"Files with gitignore: {len(docs_with_gitignore)}")
        print(
            f"Files filtered out: {len(docs_without_gitignore) - len(docs_with_gitignore)}"
        )

        if len(docs_with_gitignore) < len(docs_without_gitignore):
            print("✅ GitIgnore filtering is working correctly!")
        else:
            print("⚠️  GitIgnore filtering may not be working as expected")

    finally:
        # Clean up
        print("\nCleaning up test repository...")
        shutil.rmtree(repo_path)
        print("Integration test completed.")


if __name__ == "__main__":
    test_integration()
