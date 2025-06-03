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

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            self.logger.debug(f"File does not exist: {file_path}")
            return False

        abs_path = file_path_obj.resolve()

        # File must be within the repository
        try:
            abs_path.relative_to(self.repo_path)
        except ValueError:
            # File is outside repository, don't ignore
            self.logger.debug(f"File outside repository: {file_path}")
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
            # A pattern like "foo/" should match "foo" if it's a directory, or "foo/bar.txt".
            # So, we match pattern_without_slash against the file_path itself if it's a directory,
            # or against any directory component of file_path.
            # Or if file_path starts with pattern_without_slash + "/"
            if full_file_path.is_dir() and self._fnmatch_gitignore(file_path, pattern_without_slash):
                return True
            if self._fnmatch_gitignore(file_path, pattern_without_slash + "/*") or \
               self._fnmatch_gitignore(file_path, pattern_without_slash): # Match "dir" against "dir"
                 return True
            # Check if any parent directory component matches
            current_check_path = ""
            for part in file_path.split('/'):
                if not part: continue
                current_check_path = f"{current_check_path}{part}"
                if self._fnmatch_gitignore(current_check_path, pattern_without_slash):
                    return True
                current_check_path += "/"

            return False # If none of the above, a dir-only pattern doesn't match a file like this.


        # Handle patterns starting with '/' (absolute from git root of the .gitignore file)
        if pattern.startswith("/"):
            pattern = pattern[1:]  # Remove leading slash
            # Match from the beginning of the path relative to .gitignore dir
            return self._fnmatch_gitignore(file_path, pattern)

        # For patterns not starting with '/', and not ending with '/',
        # they can match at any directory level if no other '/' is present.
        # If '/' is present, it's a path relative to the .gitignore file's directory.
        if "/" not in pattern:
            # Pattern is like "file.txt" or "*.log"
            # It should match the filename or any directory component.
            path_parts = file_path.split("/")
            if any(self._fnmatch_gitignore(part, pattern) for part in path_parts):
                return True
            # Fallback: check against the whole relative path (e.g. pattern "foo" matching "path/to/foo")
            # This is implicitly covered by fnmatch if pattern has no wildcards, but explicit check is fine.
            # Git's behavior: "foo" matches "foo" file or dir, and "dir/foo" file or dir.
            return self._fnmatch_gitignore(file_path, pattern)


        # If pattern contains '/' (but not at start or end, handled above), it's a relative path.
        # e.g. "dir/file.log" or "dir/*.log"
        # This is also the fallback for more complex patterns not caught by specific handlers.
        # This also handles patterns with "**" by converting them to fnmatch compatible "*"
        # This is a simplification for "**" but better than nothing.
        # A more robust solution would be to convert gitignore glob to regex.
        fnmatch_pattern = pattern.replace("**", "*") # Simple ** replacement
        return self._fnmatch_gitignore(file_path, fnmatch_pattern)

        # This was part of _match_recursive_pattern, which is now removed.
        # The general fallback in _matches_pattern handles simple ** replacement.
        pass # _match_recursive_pattern removed


    def _fnmatch_gitignore(self, path: str, pattern: str) -> bool:
        """
        Perform gitignore-style pattern matching using fnmatch.
        Git patterns are case-sensitive by default on case-sensitive file systems.
        fnmatch is case-sensitive on Unix-like systems.

        Args:
            path (str): Path to match.
            pattern (str): Pattern to match against.

        Returns:
            bool: True if pattern matches, False otherwise.
        """
        # Basic checks
        if not pattern: # Empty pattern should not match anything
            return False
        if not path and pattern == ".": # Match current dir placeholder
             return True


        # fnmatch is generally good for gitignore patterns, except for '**'
        # which we've simplified to '*' before calling this for some cases.
        # Other gitignore specifics:
        # - If the pattern ends with a slash, it matches only directories. (Handled before this func)
        # - If a pattern contains a slash not at the end, it's matched relative to the .gitignore dir.
        # - If a pattern does not contain a slash, it's matched against filename and dir components.

        # Escape special characters for fnmatch if they are literal and not wildcards
        # This is complex. For now, assume patterns are valid fnmatch patterns or simple literals.
        try:
            return fnmatch.fnmatch(path, pattern)
        except (ValueError, TypeError) as e:
            self.logger.debug(f"fnmatch failed for path='{path}', pattern='{pattern}': {e}. Falling back to string check.")
            # Fallback to simple string matching if fnmatch fails (e.g. invalid pattern for fnmatch)
            # This is a very basic fallback and might not be accurate.
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
