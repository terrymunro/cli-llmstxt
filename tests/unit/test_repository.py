import unittest
from unittest.mock import patch, MagicMock, call
import tempfile # For patching tempfile.mkdtemp
import shutil   # For patching shutil.rmtree
import os       # For patching os.path.exists
from pathlib import Path # For patching Path
import git      # For git.exc.GitCommandError

# Adjust import path based on project structure
from src.llmstxt.repository import RepositoryAcquisition

class TestRepositoryAcquisition(unittest.TestCase):

    def setUp(self):
        self.repo_acquisition = RepositoryAcquisition()

    @patch('src.llmstxt.repository.git.Repo') # Mocking git.Repo
    @patch('src.llmstxt.repository.tempfile.mkdtemp')
    def test_acquire_repository_remote_url_success(self, mock_mkdtemp, mock_git_repo_cls):
        mock_temp_dir_path = '/fake/temp_dir'
        mock_mkdtemp.return_value = mock_temp_dir_path

        repo_url = "https://github.com/user/repo.git"
        returned_path = self.repo_acquisition.acquire_repository(repo_url)

        mock_mkdtemp.assert_called_once_with(prefix="llmstxt_repo_")
        mock_git_repo_cls.clone_from.assert_called_once_with(repo_url, mock_temp_dir_path)
        self.assertEqual(returned_path, mock_temp_dir_path)
        self.assertTrue(self.repo_acquisition.is_temp)
        self.assertEqual(self.repo_acquisition.repo_path, mock_temp_dir_path)
        self.assertEqual(self.repo_acquisition.temp_dir, mock_temp_dir_path)


    @patch('src.llmstxt.repository.git.Repo')
    @patch('src.llmstxt.repository.tempfile.mkdtemp')
    @patch('src.llmstxt.repository.shutil.rmtree')
    @patch('src.llmstxt.repository.os.path.exists') # To control if temp_dir exists before rmtree
    def test_acquire_repository_remote_url_clone_fails(self, mock_os_path_exists, mock_rmtree, mock_mkdtemp, mock_git_repo_cls):
        mock_temp_dir_path = '/fake/temp_dir_fail'
        mock_mkdtemp.return_value = mock_temp_dir_path
        # Simulate that the temp dir was created successfully before clone attempt
        # And it exists when cleanup is attempted
        mock_os_path_exists.return_value = True

        mock_git_repo_cls.clone_from.side_effect = git.exc.GitCommandError("clone", "failed", stderr="Clone error")

        repo_url = "https://github.com/user/repo_fail.git"
        with self.assertRaises(ValueError) as context:
            self.repo_acquisition.acquire_repository(repo_url)

        self.assertIn("Failed to clone repository", str(context.exception))
        mock_mkdtemp.assert_called_once_with(prefix="llmstxt_repo_")
        # Ensure cleanup was attempted because temp_dir was set and "existed"
        mock_os_path_exists.assert_called_once_with(mock_temp_dir_path)
        mock_rmtree.assert_called_once_with(mock_temp_dir_path)
        self.assertIsNone(self.repo_acquisition.temp_dir, "temp_dir should be reset after failed clone and cleanup")


    @patch('src.llmstxt.repository.Path')
    def test_acquire_repository_local_path_success(self, mock_path_cls):
        # Configure the mock for Path(local_path_str)
        mock_path_instance = MagicMock(spec=Path)
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        # Simulate a non-empty directory
        mock_path_instance.iterdir.return_value = iter([Path("/valid/local/path/somefile.txt")])
        # Make Path() constructor return our mock instance
        mock_path_cls.return_value = mock_path_instance

        local_path_str = "/valid/local/path"
        returned_path = self.repo_acquisition.acquire_repository(local_path_str)

        mock_path_cls.assert_called_once_with(local_path_str)
        self.assertEqual(returned_path, local_path_str)
        self.assertFalse(self.repo_acquisition.is_temp)
        self.assertEqual(self.repo_acquisition.repo_path, local_path_str)
        self.assertIsNone(self.repo_acquisition.temp_dir)

    @patch('src.llmstxt.repository.Path')
    def test_acquire_repository_local_path_not_exists(self, mock_path_cls):
        mock_path_instance = MagicMock(spec=Path)
        mock_path_instance.exists.return_value = False
        mock_path_cls.return_value = mock_path_instance

        local_path_str = "/invalid/path_not_exists"
        with self.assertRaises(ValueError) as context:
            self.repo_acquisition.acquire_repository(local_path_str)
        self.assertIn("Local path does not exist", str(context.exception))

    @patch('src.llmstxt.repository.Path')
    def test_acquire_repository_local_path_is_file(self, mock_path_cls):
        mock_path_instance = MagicMock(spec=Path)
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = False # It's a file
        mock_path_cls.return_value = mock_path_instance

        local_path_str = "/path/to/a/file.txt"
        with self.assertRaises(ValueError) as context:
            self.repo_acquisition.acquire_repository(local_path_str)
        self.assertIn("Local path is not a directory", str(context.exception))

    @patch('src.llmstxt.repository.Path')
    def test_acquire_repository_local_path_is_empty_dir(self, mock_path_cls):
        mock_path_instance = MagicMock(spec=Path)
        mock_path_instance.exists.return_value = True
        mock_path_instance.is_dir.return_value = True
        mock_path_instance.iterdir.return_value = iter([]) # Empty directory
        mock_path_cls.return_value = mock_path_instance

        local_path_str = "/path/to/empty_dir"
        with self.assertRaises(ValueError) as context:
            self.repo_acquisition.acquire_repository(local_path_str)
        self.assertIn("Local repository path is an empty directory", str(context.exception))

    @patch('src.llmstxt.repository.shutil.rmtree')
    @patch('src.llmstxt.repository.os.path.exists')
    def test_cleanup_is_temp_and_dir_exists(self, mock_os_path_exists, mock_rmtree):
        self.repo_acquisition.is_temp = True
        self.repo_acquisition.temp_dir = "/fake/temp_dir_to_clean"
        self.repo_acquisition.repo_path = "/fake/temp_dir_to_clean" # Also set repo_path
        mock_os_path_exists.return_value = True

        self.repo_acquisition.cleanup()

        mock_os_path_exists.assert_called_once_with("/fake/temp_dir_to_clean")
        mock_rmtree.assert_called_once_with("/fake/temp_dir_to_clean")
        self.assertIsNone(self.repo_acquisition.temp_dir)
        self.assertIsNone(self.repo_acquisition.repo_path)
        self.assertFalse(self.repo_acquisition.is_temp)

    @patch('src.llmstxt.repository.shutil.rmtree')
    @patch('src.llmstxt.repository.os.path.exists')
    def test_cleanup_is_not_temp(self, mock_os_path_exists, mock_rmtree):
        self.repo_acquisition.is_temp = False
        self.repo_acquisition.repo_path = "/local/repo" # Not a temp dir

        self.repo_acquisition.cleanup()

        mock_os_path_exists.assert_not_called()
        mock_rmtree.assert_not_called()
        # repo_path should remain if it wasn't a temp path
        self.assertEqual(self.repo_acquisition.repo_path, "/local/repo")
        self.assertFalse(self.repo_acquisition.is_temp)

    @patch('src.llmstxt.repository.shutil.rmtree')
    @patch('src.llmstxt.repository.os.path.exists')
    def test_cleanup_is_temp_but_dir_not_exists(self, mock_os_path_exists, mock_rmtree):
        self.repo_acquisition.is_temp = True
        self.repo_acquisition.temp_dir = "/fake/temp_dir_already_gone"
        mock_os_path_exists.return_value = False # Simulate dir does not exist

        self.repo_acquisition.cleanup()

        mock_os_path_exists.assert_called_once_with("/fake/temp_dir_already_gone")
        mock_rmtree.assert_not_called()
        self.assertIsNone(self.repo_acquisition.temp_dir)
        self.assertIsNone(self.repo_acquisition.repo_path)
        self.assertFalse(self.repo_acquisition.is_temp)

    @patch('src.llmstxt.repository.shutil.rmtree')
    @patch('src.llmstxt.repository.os.path.exists')
    def test_cleanup_temp_dir_is_none(self, mock_os_path_exists, mock_rmtree):
        self.repo_acquisition.is_temp = True
        self.repo_acquisition.temp_dir = None # temp_dir was not set or already cleared

        self.repo_acquisition.cleanup()
        mock_os_path_exists.assert_not_called() # Should check if temp_dir is not None first
        mock_rmtree.assert_not_called()
        self.assertIsNone(self.repo_acquisition.temp_dir)
        self.assertIsNone(self.repo_acquisition.repo_path)
        self.assertFalse(self.repo_acquisition.is_temp)

if __name__ == '__main__':
    unittest.main()
