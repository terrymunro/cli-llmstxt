"""
GitIgnore Handler for the AI-Powered Repository Analyzer.

This module provides gitignore file parsing and pattern matching functionality
to exclude git-ignored files from processing.
"""

import os
import logging
import fnmatch
from pathlib import Path
from typing import List, Tuple


class GitIgnoreHandler:
    """
    Handles .gitignore file parsing and file exclusion based on gitignore patterns.

    This class provides gitignore-compliant pattern matching to determine which
    files should be excluded from processing based on .gitignore rules.
    """

    def __init__(self, repo_path: str):
        """
        Initialize the GitIgnore handler.

        Args:
            repo_path (str): Path to the repository root.
        """
        self.repo_path = Path(repo_path).resolve()
        self.logger = logging.getLogger(__name__)
        # List of (pattern, is_negation, gitignore_dir) tuples
        self.ignore_patterns: List[Tuple[str, bool, Path]] = []
        self._parse_gitignore_files()

    def _parse_gitignore_files(self):
        """
        Parse all .gitignore files in the repository and build pattern list.
        """
        self.logger.info("Parsing .gitignore files...")

        # Find all .gitignore files in the repository
        gitignore_files = list(self.repo_path.rglob(".gitignore"))

        if not gitignore_files:
            self.logger.info("No .gitignore files found in repository")
            return

        for gitignore_file in gitignore_files:
            self._parse_single_gitignore(gitignore_file)

        self.logger.info(
            "Parsed %d .gitignore file(s) with %d patterns",
            len(gitignore_files),
            len(self.ignore_patterns),
        )

    def _parse_single_gitignore(self, gitignore_path: Path):
        """
        Parse a single .gitignore file and add patterns to the list.

        Args:
            gitignore_path (Path): Path to the .gitignore file.
        """
        try:
            gitignore_dir = gitignore_path.parent

            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Handle negation patterns
                    is_negation = line.startswith("!")
                    if is_negation:
                        line = line[1:]  # Remove the '!' prefix

                    # Skip empty patterns after removing '!'
                    if not line:
                        continue

                    # Store pattern with metadata
                    self.ignore_patterns.append((line, is_negation, gitignore_dir))

        except (OSError, IOError) as e:
            self.logger.warning(
                "Error parsing .gitignore file %s: %s", gitignore_path, str(e)
            )

    def should_ignore(self, file_path: str) -> bool:
        """
        Check if a file should be ignored based on gitignore patterns.

        Args:
            file_path (str): Absolute path to the file to check.

        Returns:
            bool: True if the file should be ignored, False otherwise.
        """
        if not self.ignore_patterns:
            return False

        file_path_obj = Path(file_path).resolve()

        # File must be within the repository
        try:
            file_path_obj.relative_to(self.repo_path)
        except ValueError:
            # File is outside repository, don't ignore
            return False

        # Track ignore state (can be overridden by negation patterns)
        is_ignored = False

        # Process patterns in order (later patterns can override earlier ones)
        for pattern, is_negation, gitignore_dir in self.ignore_patterns:
            # Check if this gitignore file applies to this file's location
            try:
                file_relative_to_gitignore = file_path_obj.relative_to(gitignore_dir)
                file_path_for_pattern = str(file_relative_to_gitignore).replace(
                    os.sep, "/"
                )
            except ValueError:
                # File is not under this gitignore's directory
                continue

            if self._matches_pattern(file_path_for_pattern, pattern, file_path_obj):
                if is_negation:
                    is_ignored = False  # Negation pattern un-ignores the file
                else:
                    is_ignored = True  # Regular pattern ignores the file

        return is_ignored

    def _matches_pattern(
        self, file_path: str, pattern: str, full_file_path: Path
    ) -> bool:
        """
        Check if a file path matches a gitignore pattern.

        Args:
            file_path (str): Relative file path with forward slashes.
            pattern (str): Gitignore pattern to match against.
            full_file_path (Path): Full Path object for directory checks.

        Returns:
            bool: True if the pattern matches, False otherwise.
        """
        # Handle directory-only patterns (ending with '/')
        if pattern.endswith("/"):
            pattern_without_slash = pattern[:-1]
            # For directory patterns, check if any part of the path matches
            path_parts = file_path.split("/")
            # Remove filename if this is a file
            if not full_file_path.is_dir():
                path_parts = path_parts[:-1]

            # Check if any directory in the path matches the pattern
            for part in path_parts:
                if self._fnmatch_gitignore(part, pattern_without_slash):
                    return True
            # Also check if the pattern matches from root
            return self._fnmatch_gitignore(file_path, pattern_without_slash + "/**")

        # Handle patterns starting with '/' (absolute from git root)
        if pattern.startswith("/"):
            pattern = pattern[1:]  # Remove leading slash
            # Match from the beginning of the path
            return self._fnmatch_gitignore(file_path, pattern)

        # Handle patterns with '**' (recursive directory matching)
        if "**" in pattern:
            return self._match_recursive_pattern(file_path, pattern)

        # Handle patterns with directory separators
        if "/" in pattern:
            return self._fnmatch_gitignore(file_path, pattern)

        # Simple filename pattern - match against any part of the path
        path_parts = file_path.split("/")
        filename = path_parts[-1]  # Just the filename

        # Check if pattern matches the filename
        if self._fnmatch_gitignore(filename, pattern):
            return True

        # Check if pattern matches any directory name in the path
        for part in path_parts[:-1]:  # Exclude the filename
            if self._fnmatch_gitignore(part, pattern):
                return True

        # Also check if the pattern matches the entire path
        return self._fnmatch_gitignore(file_path, pattern)

    def _match_recursive_pattern(self, file_path: str, pattern: str) -> bool:
        """
        Handle patterns with '**' for recursive directory matching.

        Args:
            file_path (str): File path to match.
            pattern (str): Pattern with '**' wildcards.

        Returns:
            bool: True if pattern matches, False otherwise.
        """
        # Convert '**' to a regex-like pattern for fnmatch
        # '**/' matches zero or more directories
        pattern_parts = pattern.split("**")

        if len(pattern_parts) == 2:
            prefix, suffix = pattern_parts
            prefix = prefix.rstrip("/")
            suffix = suffix.lstrip("/")

            # Handle case where pattern is just '**'
            if not prefix and not suffix:
                return True

            # Handle '**' at the beginning
            if not prefix:
                return file_path.endswith(suffix) or ("/" + suffix) in file_path

            # Handle '**' at the end
            if not suffix:
                return file_path.startswith(prefix)

            # Handle '**' in the middle
            return file_path.startswith(prefix) and (
                file_path.endswith(suffix) or ("/" + suffix) in file_path
            )

        # Multiple '**' patterns - use simple approach
        return self._fnmatch_gitignore(file_path, pattern.replace("**", "*"))

    def _fnmatch_gitignore(self, path: str, pattern: str) -> bool:
        """
        Perform gitignore-style pattern matching using fnmatch.

        Args:
            path (str): Path to match.
            pattern (str): Pattern to match against.

        Returns:
            bool: True if pattern matches, False otherwise.
        """
        try:
            return fnmatch.fnmatch(path, pattern)
        except (ValueError, TypeError):
            # Fallback to simple string matching if fnmatch fails
            return pattern in path

    def get_ignore_patterns_for_exclusions(self) -> List[str]:
        """
        Get gitignore patterns in a format suitable for existing exclusion lists.

        Returns:
            List[str]: List of patterns that can be used with glob matching.
        """
        patterns: List[str] = []
        for pattern, is_negation, _ in self.ignore_patterns:
            if not is_negation:  # Only include non-negation patterns
                # Convert gitignore patterns to glob patterns where possible
                if not pattern.startswith("/"):
                    pattern = f"**/{pattern}"
                if pattern.endswith("/"):
                    pattern = f"{pattern[:-1]}/**"
                patterns.append(pattern)

        return patterns

    def get_stats(self) -> dict[str, int]:
        """
        Get statistics about loaded gitignore patterns.

        Returns:
            dict[str, int]: Statistics about gitignore patterns.
        """
        total_patterns = len(self.ignore_patterns)
        negation_patterns = sum(
            1 for _, is_negation, _ in self.ignore_patterns if is_negation
        )
        regular_patterns = total_patterns - negation_patterns

        return {
            "total_patterns": total_patterns,
            "regular_patterns": regular_patterns,
            "negation_patterns": negation_patterns,
            "gitignore_files_found": len(
                set(gitignore_dir for _, _, gitignore_dir in self.ignore_patterns)
            ),
        }
