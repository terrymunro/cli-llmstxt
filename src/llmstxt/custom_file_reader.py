"""
Custom file reader module for the AI-Powered Repository Analyzer.

This module provides direct file reading functionality without relying on LlamaIndex plugins.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from llmstxt.gitignore_handler import GitIgnoreHandler


class CustomFileReader:
    """
    Custom file reader that directly reads files from a repository.

    This class provides an alternative to SimpleDirectoryReader when the llama-index-readers-file
    plugin is not available or not recognized at runtime.
    """

    def __init__(self):
        """Initialize the custom file reader."""
        self.logger = logging.getLogger(__name__)

    def load_data(
        self,
        repo_path: str,
        extensions: List[str],
        exclusions: List[str],
        max_file_size_kb: int = 256,
        gitignore_handler: Optional["GitIgnoreHandler"] = None,
    ) -> List[Dict]:
        """
        Load documents from the repository.

        Args:
            repo_path (str): Path to the repository.
            extensions (List[str]): List of file extensions to process.
            exclusions (List[str]): List of patterns to exclude.
            max_file_size_kb (int): Maximum file size in KB to process.
            gitignore_handler (Optional[GitIgnoreHandler]): GitIgnoreHandler instance for ignore patterns.

        Returns:
            List[Dict]: List of loaded documents with metadata.
        """
        self.logger.info(
            f"Loading documents from {repo_path} using custom file reader..."
        )

        # Normalize extensions (case-insensitive, handle with/without dot)
        normalized_extensions = [ext.lower().lstrip(".") for ext in extensions]
        self.logger.info(f"Using file extensions: {normalized_extensions}")

        # Create a list to store documents
        documents = []

        # Check if directory exists
        repo_dir = Path(repo_path)
        if not repo_dir.exists() or not repo_dir.is_dir():
            self.logger.error(
                f"Repository path does not exist or is not a directory: {repo_path}"
            )
            raise ValueError(f"Invalid repository path: {repo_path}")

        # Log files in directory for debugging
        self.logger.info("Repository contents:")
        for root, dirs, files in os.walk(repo_path):
            # Future enhancement: allow pruning of dirs, e.g., based on gitignore or hidden status
            # For now, os.walk default behavior for hidden dirs is fine.
            for file_name in files:
                file_path = Path(root) / file_name

                # Only skip hidden files (files starting with a dot)
                # This doesn't skip files in hidden directories (e.g. '.git/config')
                # if the hidden directory itself is not skipped by os.walk.
                if file_name.startswith(".") and file_name != ".":
                    self.logger.debug(f"Skipping hidden file: {file_path}")
                    continue

                # Ensure it's a file (resolve symlinks and check target)
                if not file_path.is_file():
                    self.logger.debug(
                        f"Skipping non-file path (e.g., symlink to dir, broken symlink): {file_path}"
                    )
                    continue

                # Check extension (case-insensitive)
                file_ext = file_path.suffix.lstrip(".").lower()
                if normalized_extensions and file_ext not in normalized_extensions:
                    self.logger.debug(
                        f"Skipping file with unmatched extension: {file_path}"
                    )
                    continue

                # Skip if matches exclusion pattern
                if any(file_path.match(pattern) for pattern in exclusions):
                    self.logger.info(f"Skipping excluded file: {file_path}")
                    continue

                # Skip if gitignore says to ignore this file
                if gitignore_handler and gitignore_handler.should_ignore(str(file_path)):
                    self.logger.info(f"Skipping git-ignored file: {file_path}")
                    continue

                # Skip if file is too large
                try:
                    file_size_kb = os.path.getsize(file_path) / 1024
                    if max_file_size_kb > 0 and file_size_kb > max_file_size_kb:
                        self.logger.warning(
                            f"Skipping file due to size limit ({file_size_kb:.2f}KB): {file_path}"
                        )
                        continue
                except OSError as e:
                    self.logger.warning(f"Could not get size of file {file_path}: {e}")
                    continue


                # Read file content
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Skip if empty
                    if not content.strip():
                        self.logger.warning(f"Skipping empty file: {file_path}")
                        continue

                    # Create a document object with compatible structure
                    from llama_index.core.schema import Document

                    doc = Document(text=content, metadata={"file_path": str(file_path)})
                    documents.append(doc)
                    self.logger.info(f"Loaded file: {file_path}")

                except Exception as e:
                    self.logger.warning(f"Error reading file {file_path}: {str(e)}")
                    continue

        self.logger.info(f"Loaded {len(documents)} documents")
        return documents
