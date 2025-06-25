import unittest
from unittest.mock import patch, MagicMock
import argparse
from pathlib import Path
import os # For OPENAI_API_KEY testing if needed by validate_arguments

# Adjust import path based on project structure
# Assuming 'src' is the source directory and tests are run from project root
from src.llmstxt import cli
from src.llmstxt.config import (
    DEFAULT_CODE_EXTENSIONS,
    DEFAULT_OUTPUT_DIR,
    MAX_FILE_SIZE_KB,
    MAX_OVERALL_SUMMARY_INPUT_CHARS
)

class TestCli(unittest.TestCase):

    @patch('sys.argv', ['llmstxt', 'my_repo_path'])
    def test_parse_arguments_required_only(self):
        args = cli.parse_arguments()
        self.assertEqual(args.repo_specifier, 'my_repo_path')
        # Check default values from config
        self.assertEqual(args.code_extensions, DEFAULT_CODE_EXTENSIONS)
        # argparse converts Path default to string if not specified by type=Path in add_argument
        # In cli.py, output_dir has type=Path, so it should be a Path object.
        self.assertEqual(args.output_dir, DEFAULT_OUTPUT_DIR)
        self.assertEqual(args.max_file_size_kb, MAX_FILE_SIZE_KB)
        self.assertEqual(args.max_overall_summary_input_chars, MAX_OVERALL_SUMMARY_INPUT_CHARS)
        self.assertFalse(args.trigger_interface_analysis)
        self.assertTrue(args.respect_gitignore) # Default from argparse action
        self.assertFalse(args.ignore_gitignore) # Default from argparse action

    @patch('sys.argv', [
        'llmstxt', 'another_repo',
        '--code_extensions', '.py,.md',
        '--output_dir', '/tmp/output',
        '--max_file_size_kb', '100',
        '--max_overall_summary_input_chars', '50000',
        '--trigger_interface_analysis',
        '--ignore_gitignore'
    ])
    def test_parse_arguments_all_provided(self):
        args = cli.parse_arguments()
        self.assertEqual(args.repo_specifier, 'another_repo')
        self.assertEqual(args.code_extensions, '.py,.md')
        self.assertEqual(args.output_dir, Path('/tmp/output')) # Should be Path object
        self.assertEqual(args.max_file_size_kb, 100)
        self.assertEqual(args.max_overall_summary_input_chars, 50000)
        self.assertTrue(args.trigger_interface_analysis)
        # ignore_gitignore=True should make respect_gitignore=False (handled in validate_arguments, not parse_arguments directly)
        # parse_arguments sets defaults from add_argument. Validation step may alter them.
        # For this test, we check what parse_arguments itself does.
        # The interaction is tested in validate_arguments.
        self.assertTrue(args.respect_gitignore) # Default is True
        self.assertTrue(args.ignore_gitignore) # Set by argument

    def test_validate_arguments_valid_new_dir(self):
        # Mock Path.mkdir for output_dir validation when dir does not exist
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False # To trigger mkdir
            args = argparse.Namespace(
                output_dir=Path('valid_output_new'), # Use Path object
                max_file_size_kb=100,
                max_overall_summary_input_chars=10000,
                ignore_gitignore=False,
                respect_gitignore=True
            )
            is_valid, msg = cli.validate_arguments(args)
            self.assertTrue(is_valid)
            self.assertEqual(msg, "")
            mock_mkdir.assert_called_once_with(parents=True)

    def test_validate_arguments_valid_existing_dir(self):
        # Mock Path.mkdir for output_dir validation when dir exists
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.is_dir') as mock_is_dir:
            mock_exists.return_value = True
            mock_is_dir.return_value = True
            args = argparse.Namespace(
                output_dir=Path('valid_output_existing'), # Use Path object
                max_file_size_kb=100,
                max_overall_summary_input_chars=10000,
                ignore_gitignore=False,
                respect_gitignore=True
            )
            is_valid, msg = cli.validate_arguments(args)
            self.assertTrue(is_valid)
            self.assertEqual(msg, "")
            mock_mkdir.assert_not_called()

    def test_validate_arguments_output_dir_is_file(self):
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.is_dir') as mock_is_dir:
            mock_exists.return_value = True
            mock_is_dir.return_value = False # Simulate output_dir being a file
            args = argparse.Namespace(
                output_dir=Path('path_is_a_file'), # Use Path object
                max_file_size_kb=100,
                max_overall_summary_input_chars=10000
                # gitignore flags not relevant for this specific validation
            )
            is_valid, msg = cli.validate_arguments(args)
            self.assertFalse(is_valid)
            self.assertIn("Output path exists but is not a directory", msg)

    def test_validate_arguments_output_dir_creation_fails(self):
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")) as mock_mkdir, \
             patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False # To trigger mkdir
            args = argparse.Namespace(
                output_dir=Path('uncreatable_output'), # Use Path object
                max_file_size_kb=100,
                max_overall_summary_input_chars=10000
            )
            is_valid, msg = cli.validate_arguments(args)
            self.assertFalse(is_valid)
            self.assertIn("Error creating output directory: Permission denied", msg)
            mock_mkdir.assert_called_once_with(parents=True)

    def test_validate_arguments_negative_max_file_size(self):
        args = argparse.Namespace(
            output_dir=Path('any_output'),
            max_file_size_kb=-5, # Invalid
            max_overall_summary_input_chars=10000
        )
        # Need to mock Path.exists and Path.is_dir if output_dir validation runs first
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            is_valid, msg = cli.validate_arguments(args)
            self.assertFalse(is_valid)
            self.assertEqual(msg, "max_file_size_kb must be non-negative")

    def test_validate_arguments_zero_max_overall_summary_chars(self):
        args = argparse.Namespace(
            output_dir=Path('any_output'),
            max_file_size_kb=100,
            max_overall_summary_input_chars=0 # Invalid
        )
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            is_valid, msg = cli.validate_arguments(args)
            self.assertFalse(is_valid)
            self.assertEqual(msg, "max_overall_summary_input_chars must be positive")

    def test_validate_arguments_ignore_gitignore_sets_respect_false(self):
        args = argparse.Namespace(
            output_dir=Path('any_output'),
            max_file_size_kb=100,
            max_overall_summary_input_chars=10000,
            ignore_gitignore=True, # This should make respect_gitignore False
            respect_gitignore=True # Initial value before validation
        )
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            is_valid, msg = cli.validate_arguments(args)
            self.assertTrue(is_valid) # This combination is valid
            self.assertFalse(args.respect_gitignore) # Check that it was modified

    def test_validate_arguments_respect_gitignore_default(self):
        args = argparse.Namespace(
            output_dir=Path('any_output'),
            max_file_size_kb=100,
            max_overall_summary_input_chars=10000,
            ignore_gitignore=False,
            respect_gitignore=True # Default or explicitly set
        )
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            is_valid, msg = cli.validate_arguments(args)
            self.assertTrue(is_valid)
            self.assertTrue(args.respect_gitignore)

    # The OPENAI_API_KEY check in validate_arguments is a warning, not an invalidation.
    # We can test that it proceeds correctly.
    @patch.dict(os.environ, clear=True) # Ensure OPENAI_API_KEY is not set
    def test_validate_arguments_no_openai_key(self):
        # This test implicitly checks that no error occurs if OPENAI_API_KEY is missing,
        # as validate_arguments currently only warns about it in main.py, not here.
        args = argparse.Namespace(
            output_dir=Path('any_output'),
            max_file_size_kb=100,
            max_overall_summary_input_chars=10000,
            ignore_gitignore=False,
            respect_gitignore=True
        )
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.is_dir', return_value=True):
            is_valid, msg = cli.validate_arguments(args)
            self.assertTrue(is_valid) # Should still be valid
            self.assertEqual(msg, "")


if __name__ == '__main__':
    unittest.main()
