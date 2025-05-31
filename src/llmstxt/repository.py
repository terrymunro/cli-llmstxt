"""
Repository Acquisition Module for the AI-Powered Repository Analyzer.

This module handles repository access, whether local or remote.
"""

import os
import tempfile
import shutil
from pathlib import Path
import logging
import git
from git import Repo


class RepositoryAcquisition:
    """
    Handles repository acquisition from either a local path or a GitHub URL.
    """

    def __init__(self):
        """Initialize the repository acquisition module."""
        self.temp_dir = None
        self.repo_path = None
        self.is_temp = False
        self.logger = logging.getLogger(__name__)

    def acquire_repository(self, repo_specifier):
        """
        Determine if input is URL or local path and handle accordingly.

        Args:
            repo_specifier (str): Path to local repository or GitHub URL.

        Returns:
            str: Path to the repository.

        Raises:
            ValueError: If the repository cannot be acquired.
        """
        # Check if repo_specifier is a URL
        if repo_specifier.startswith(("http://", "https://")):
            self.logger.info(f"Cloning repository from {repo_specifier}...")
            return self.clone_repository(repo_specifier)
        else:
            self.logger.info(f"Using local repository at {repo_specifier}...")
            return self.validate_local_path(repo_specifier)

    def clone_repository(self, url):
        """
        Clone GitHub repository to temporary directory.

        Args:
            url (str): GitHub repository URL.

        Returns:
            str: Path to the cloned repository.

        Raises:
            ValueError: If the repository cannot be cloned.
        """
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix="repo_analyzer_")
            self.is_temp = True

            # Clone repository
            Repo.clone_from(url, self.temp_dir)
            self.repo_path = self.temp_dir
            self.logger.info(f"Repository cloned to {self.repo_path}")

            return self.repo_path
        except git.exc.GitCommandError as e:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            self.logger.error(f"Git error: {str(e)}")
            raise ValueError(f"Failed to clone repository: {str(e)}")
        except Exception as e:
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            self.logger.error(f"Error: {str(e)}")
            raise ValueError(f"Failed to clone repository: {str(e)}")

    def validate_local_path(self, path):
        """
        Ensure local path exists and is a valid repository.

        Args:
            path (str): Path to local repository.

        Returns:
            str: Validated path to the repository.

        Raises:
            ValueError: If the path is not valid.
        """
        repo_path = Path(path)

        # Check if path exists
        if not repo_path.exists():
            self.logger.error(f"Path does not exist: {path}")
            raise ValueError(f"Path does not exist: {path}")

        # Check if path is a directory
        if not repo_path.is_dir():
            self.logger.error(f"Path is not a directory: {path}")
            raise ValueError(f"Path is not a directory: {path}")

        # Check if path contains files (basic validation)
        if not any(repo_path.iterdir()):
            self.logger.error(f"Directory is empty: {path}")
            raise ValueError(f"Directory is empty: {path}")

        self.repo_path = str(repo_path)
        self.is_temp = False
        return self.repo_path

    def cleanup(self):
        """
        Remove temporary directory if created.
        """
        if self.is_temp and self.temp_dir and os.path.exists(self.temp_dir):
            self.logger.info(f"Cleaning up temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            self.repo_path = None
            self.is_temp = False
