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
        Rules are based on https://git-scm.com/docs/gitignore.

        Args:
            file_path (str): Relative file path from gitignore_dir, using forward slashes.
            pattern (str): Gitignore pattern.
            full_file_path (Path): Absolute Path object for the file/directory being checked.
                                   Used to determine if a matched path is a directory.
            # gitignore_dir (Path): Base directory of the .gitignore file. Implicitly self.repo_path for patterns
            #                     from repo root .gitignore, or parent of specific .gitignore.
            #                     The file_path is already relative to the correct gitignore_dir.

        Returns:
            bool: True if the pattern matches, False otherwise.
        """
        original_pattern = pattern # For logging or specific checks if needed

        # Normalize pattern: remove trailing spaces unless they are escaped
        # Git automatically strips unescaped trailing spaces.
        # For simplicity, we assume patterns are already stripped by _parse_single_gitignore.
        # If a pattern has specific escaped spaces, fnmatch should handle them.

        # Handle directory-only patterns (trailing '/')
        is_dir_pattern = pattern.endswith('/')
        if is_dir_pattern:
            pattern = pattern[:-1]
            if not pattern: # Pattern was just "/"
                return False # Should not happen with prior stripping, but good to guard.

        # Handle patterns with "**" - these are complex and fnmatch handles them well.
        if "**" in pattern:
            # If original was "foo/**/", pattern is now "foo/**".
            # This should match "foo/bar/" or "foo/bar/baz.txt" if "foo/bar" is part of path.
            # The is_dir_pattern check will be applied after fnmatch.
            match = self._fnmatch_gitignore(file_path, pattern)
            if match and is_dir_pattern:
                # Pattern "dir/" (effective "dir"):
                # - file_path "dir": match if full_file_path is_dir.
                # - file_path "dir/file": match. (dir component matches)
                # - file_path "other/dir": match if "other/dir" (full_file_path) is_dir.
                # - file_path "other/dir/file": match. (dir component matches)

                # If fnmatch says file_path 'a/b/c' matches pattern 'a/b', and is_dir_pattern was true,
                # we need to check if 'a/b' is a directory.
                # This is hard because fnmatch doesn't tell us *which part* of file_path matched.
                # A common interpretation: if a dir pattern like "build/" matches "build/foo.o",
                # it's because "build" is a directory.
                # If the full file_path matches the pattern (e.g. file_path="build", pattern="build")
                if file_path == pattern:
                    return full_file_path.is_dir()
                # If file_path starts with pattern + "/" (e.g. file_path="build/foo", pattern="build")
                if file_path.startswith(pattern + "/"):
                    return True # Implies the 'pattern' part refers to a directory
                # For more complex ** cases like "foo/**/bar/" this gets harder.
                # For now, trust that if fnmatch works, the structure implies dir for **.
                # A more robust check might be needed if this proves insufficient.
                # A simple check: if the matched path is not a directory, but pattern expects one.
                if not full_file_path.is_dir() and not '/' in file_path[len(pattern):]:
                     # e.g. pattern `foo/`, file `foo` (a file). file_path=`foo`, pattern=`foo`.
                     # Here, file_path[len(pattern):] is empty.
                     return False
            return match

        # Handle patterns starting with "/" (anchored to gitignore_dir)
        if pattern.startswith('/'):
            pattern = pattern[1:]
            # file_path is already relative to gitignore_dir.
            match = self._fnmatch_gitignore(file_path, pattern)
            if match and is_dir_pattern:
                # Path "foo" (file) vs pattern "/foo/" (now "foo")
                if file_path == pattern:
                    return full_file_path.is_dir()
                # Path "foo/bar.txt" vs pattern "/foo/" (now "foo")
                # This implies 'foo' must be a directory.
                # fnmatch would match "foo/bar.txt" with "foo*".
                # We need to ensure that if pattern is "foo", it matches "foo/" path segment.
                if file_path.startswith(pattern + "/"):
                    return True
                return False # Did not match directory structure
            return match

        # Handle other patterns containing "/" (not starting with "/", no "**")
        # These are relative to gitignore_dir.
        # e.g., "foo/bar" or "src/*.c"
        if "/" in pattern:
            match = self._fnmatch_gitignore(file_path, pattern)
            if match and is_dir_pattern:
                if file_path == pattern:
                    return full_file_path.is_dir()
                if file_path.startswith(pattern + "/"): # e.g. pattern "doc/", file "doc/readme.txt"
                    return True
                # If pattern "build/logs" (from "build/logs/") matches file_path "build/logs/today.log"
                # this implies "build/logs" is a directory.
                # This is usually fine. Consider if full_file_path.is_dir() is needed for exact match.
                # If pattern `foo/bar/` (now `foo/bar`) matches filepath `foo/bar` (a file), then no match.
                if file_path == pattern and not full_file_path.is_dir():
                    return False
            return match

        # Handle patterns without "/" (e.g., "*.log", "foo")
        # These can match at any level.
        # file_path is like "some/path/to/file.log"
        # pattern is like "*.log" or "foo"

        # 1. Check against the basename of the file_path
        if self._fnmatch_gitignore(Path(file_path).name, pattern):
            if is_dir_pattern:
                # Pattern "foo/", file_path "dir/foo". Basename "foo" matches.
                # Check if full_file_path (".../dir/foo") is a directory.
                return full_file_path.is_dir()
            return True # Filename matches, and not a dir-only pattern for the filename itself.

        # 2. If is_dir_pattern, it implies the pattern refers to a directory name.
        #    This directory could be anywhere in the path.
        #    e.g. pattern "target/" (now "target"), file_path "project/target/file.o"
        #    This should match because "project/target" is a directory.
        if is_dir_pattern:
            # Check if any directory component in file_path matches 'pattern'
            # and that component is indeed a directory in the filesystem.
            # file_path is "a/b/c/d.txt", pattern "b" (from "b/")
            # We need to check if "a/b" is a directory.
            current_path_parts = Path(file_path).parts
            for i in range(len(current_path_parts)):
                # Check if the directory segment itself matches
                if self._fnmatch_gitignore(current_path_parts[i], pattern):
                    # Construct the path to this directory segment
                    # It's relative to gitignore_dir. To check is_dir, need absolute or relative to CWD.
                    # full_file_path is absolute. gitignore_dir is absolute.
                    # Path relative to repo_path: gitignore_dir.relative_to(self.repo_path)
                    # Path of current segment: gitignore_dir.joinpath(*current_path_parts[:i+1])

                    # Simpler: if file_path is "a/b/c.txt" and pattern is "b" (from "b/")
                    # this means we are checking if "a/b" is a directory.
                    # This is true if file_path starts with "a/b/"
                    # This means path_to_check = '.../b/'
                    # This is equivalent to: file_path contains 'pattern/' segment.
                    if (pattern + "/") in file_path: # e.g. "b/" in "a/b/c.txt"
                         return True
            return False # No directory component matched the dir_pattern.

        # 3. For a non-dir pattern without slashes (e.g. "foo", "*.c")
        #    It should match if any component of the path matches, or the whole path.
        #    This is often interpreted as `**/pattern` or `**/pattern/**` if we were to make it explicit.
        #    The current `_fnmatch_gitignore` will do exact match or simple glob on `file_path`.
        #    e.g. pattern "test", path "src/test/main.c" -> fnmatch("src/test/main.c", "test") is false.
        #    We need to check components.
        #    `Path(file_path).name` was already checked.
        #    So check intermediate directory names.
        path_parts = Path(file_path).parts
        if len(path_parts) > 1: # If there are directory components
            for part in path_parts[:-1]: # Iterate over directory components
                if self._fnmatch_gitignore(part, pattern):
                    return True

        # Fallback: check if the pattern matches the entire relative path string.
        # This handles cases like pattern "foo" and file_path "foo" (a file at gitignore_dir level).
        # This was implicitly covered by basename check if path_parts has only 1 element.
        # If pattern="foo" and file_path="foo", Path(file_path).name is "foo", matches.
        # If pattern="internal.h" and file_path="include/internal.h", basename matches.
        # If pattern="archive" and file_path="src/archive/old.zip", basename is "old.zip", dir part "archive" matches.

        # If we reach here, it means:
        # - Basename didn't match (or if it did, is_dir_pattern made it false).
        # - If is_dir_pattern, no directory component matched.
        # - If not is_dir_pattern, no directory component matched pattern.
        # This implies no match.
        return False


    def _match_recursive_pattern(self, file_path: str, pattern: str) -> bool:
        """
        Handle patterns with '**' for recursive directory matching.

        Args:
            file_path (str): File path to match.
            pattern (str): Pattern with '**' wildcards.

        Returns:
            bool: True if pattern matches, False otherwise.
        """
        # fnmatch in Python's standard library is generally capable of handling '**'
        # in a way that's compatible with .gitignore usage, especially when paths
        # are normalized to use forward slashes.
        # For example:
        # fnmatch.fnmatch('a/b/c/d.txt', 'a/**/d.txt') -> True
        # fnmatch.fnmatch('a/d.txt', 'a/**/d.txt') -> True (zero directories for **)
        # fnmatch.fnmatch('foo.txt', '**/foo.txt') -> True
        # fnmatch.fnmatch('a/b/foo.txt', '**/foo.txt') -> True
        # fnmatch.fnmatch('a/b/foo.txt', 'a/**') -> True

        # If the pattern is literally just "**", it should match everything.
        # This is a common interpretation for glob patterns.
        if pattern == "**":
            return True

        # Otherwise, delegate directly to fnmatch.
        # The key is that file_path and pattern are already normalized (e.g. forward slashes).
        return self._fnmatch_gitignore(file_path, pattern)

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
            # Ensure path and pattern are strings, though type hints should guarantee this
            if not isinstance(path, str) or not isinstance(pattern, str):
                self.logger.warning(
                    f"fnmatch_gitignore called with non-string arguments: path type {type(path)}, pattern type {type(pattern)}"
                )
                return False
            return fnmatch.fnmatch(path, pattern)
        except Exception as e:
            # Log unexpected errors during fnmatch processing but treat as no match
            self.logger.warning(
                f"Error during fnmatch for path='{path}', pattern='{pattern}': {e}"
            )
            return False

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
