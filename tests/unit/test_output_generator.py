import unittest
from unittest.mock import patch, mock_open, call
import tempfile
from pathlib import Path
import logging

from src.llmstxt.output_generator import OutputGenerator

# Suppress logging during tests for cleaner output
logging.disable(logging.CRITICAL)

class TestOutputGenerator(unittest.TestCase):

    def test_init(self):
        og = OutputGenerator(output_dir="test_out_dir")
        self.assertEqual(og.output_dir, Path("test_out_dir")) # OutputGenerator converts to Path

    def test_generate_full_output_with_interfaces(self):
        file_summaries = {
            "file1.py": "### Summary of file1.py\n\nSummary content 1",
            "file2.md": "### Summary of file2.md\n\nSummary content 2",
        }
        interface_descriptions = {
            "file1.py": "### Inferred Interface for file1.py\n\nInterface content for file1.py",
            "another.py": "### Inferred Interface for another.py\n\nInterface for another.py"
        }
        og = OutputGenerator(output_dir=Path("dummy_output")) # Pass Path object
        full_output = og.generate_full_output(file_summaries, interface_descriptions)

        self.assertIn("# Repository Analysis - Detailed Report", full_output)
        self.assertIn("## File Summaries", full_output)
        self.assertIn("### Summary of file1.py\n\nSummary content 1", full_output)
        self.assertIn("### Summary of file2.md\n\nSummary content 2", full_output)

        self.assertIn("## Inferred Interfaces", full_output)
        # Ensure order of interface descriptions is maintained (sorted by file path)
        # The code sorts keys, so 'another.py' comes before 'file1.py'
        expected_interface_order_substr = ("### Inferred Interface for another.py\n\nInterface for another.py\n\n"
                                           "----------------------------------------\n\n"
                                           "### Inferred Interface for file1.py\n\nInterface content for file1.py")
        self.assertIn(expected_interface_order_substr, full_output)


    def test_generate_full_output_without_interfaces(self):
        file_summaries = {
            "file1.py": "### Summary of file1.py\n\nSummary content 1",
        }
        interface_descriptions = {} # Empty
        og = OutputGenerator(output_dir=Path("dummy_output"))
        full_output = og.generate_full_output(file_summaries, interface_descriptions)

        self.assertIn("## File Summaries", full_output)
        self.assertIn("### Summary of file1.py\n\nSummary content 1", full_output)
        self.assertNotIn("## Inferred Interfaces", full_output)
        self.assertNotIn("----------------------------------------", full_output) # Separator should not be there


    def test_generate_full_output_empty_summaries_and_interfaces(self):
        file_summaries = {}
        interface_descriptions = {}
        og = OutputGenerator(output_dir=Path("dummy_output"))
        full_output = og.generate_full_output(file_summaries, interface_descriptions)

        self.assertIn("# Repository Analysis - Detailed Report", full_output)
        self.assertIn("## File Summaries", full_output) # Section header still present
        self.assertNotIn("### Summary of", full_output) # No actual summaries
        self.assertNotIn("## Inferred Interfaces", full_output)


    def test_write_output_files_success(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir_path = Path(tmpdir_name)
            og = OutputGenerator(output_dir=tmpdir_path)
            full_content = "This is the full content."
            summary_content = "This is the summary content."

            # OutputGenerator's __init__ calls self.output_dir.mkdir
            # No need to mock Path.mkdir explicitly unless we want to check its call.
            # Here, we rely on TemporaryDirectory to create tmpdir_path.

            mock_file_open = mock_open()
            with patch('builtins.open', mock_file_open):
                output_files = og.write_output_files(full_content, summary_content)

                expected_full_path = tmpdir_path / "llms-full.txt"
                expected_summary_path = tmpdir_path / "llms.txt"

                self.assertEqual(output_files["full_output"], str(expected_full_path))
                self.assertEqual(output_files["summary_output"], str(expected_summary_path))

                # Check calls to open in the correct order
                expected_open_calls = [
                    call(expected_full_path, "w", encoding="utf-8"),
                    call(expected_summary_path, "w", encoding="utf-8"),
                ]
                mock_file_open.assert_has_calls(expected_open_calls, any_order=False)

                # Check content written
                # Get all calls to the write method of the mock file object
                write_calls = mock_file_open().write.call_args_list
                self.assertEqual(len(write_calls), 2) # Should be two write calls
                self.assertEqual(write_calls[0][0][0], full_content)
                self.assertEqual(write_calls[1][0][0], summary_content)

    def test_write_output_files_io_error_on_first_file(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir_path = Path(tmpdir_name)
            og = OutputGenerator(output_dir=tmpdir_path)

            # Simulate IOError only on the first 'open' call
            mock_file_open = mock_open()
            mock_file_open.side_effect = [IOError("Disk full on first file"), mock_open().return_value]

            with patch('builtins.open', mock_file_open):
                with self.assertRaises(IOError) as context:
                    og.write_output_files("full content", "summary content")
                self.assertIn("Disk full on first file", str(context.exception))
                # Ensure it tried to open the first file
                expected_full_path = tmpdir_path / "llms-full.txt"
                mock_file_open.assert_any_call(expected_full_path, "w", encoding="utf-8")


    def test_write_output_files_io_error_on_second_file(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            tmpdir_path = Path(tmpdir_name)
            og = OutputGenerator(output_dir=tmpdir_path)

            # Simulate IOError on the second 'open' call
            mock_file_opener = mock_open()
            # First call (llms-full.txt) is fine, second (llms.txt) raises IOError
            mock_file_opener.side_effect = [mock_open().return_value, IOError("Disk full on second file")]

            with patch('builtins.open', mock_file_opener):
                with self.assertRaises(IOError) as context:
                    og.write_output_files("full content", "summary content")
                self.assertIn("Disk full on second file", str(context.exception))

                # Ensure it successfully opened and wrote the first file
                expected_full_path = tmpdir_path / "llms-full.txt"
                mock_file_opener.assert_any_call(expected_full_path, "w", encoding="utf-8")
                # Check that write was called for the first file's content
                # This requires the mock_open().return_value to be consistent for the first call
                # For simplicity, we trust the first write happened if the second open call was made and failed.
                # A more complex mock setup would be needed to track individual file handle writes with side_effect list.

if __name__ == '__main__':
    # Re-enable logging if running tests directly for debugging
    # logging.disable(logging.NOTSET)
    unittest.main()
