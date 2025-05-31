"""
Output Generation Module for the AI-Powered Repository Analyzer.

This module formats and writes output files with analysis results.
"""

import logging
from pathlib import Path
from typing import Dict


class OutputGenerator:
    """
    Formats and writes output files with analysis results.
    """

    def __init__(self, output_dir: str):
        """
        Initialize the output generator.

        Args:
            output_dir (str): Directory to save output files.
        """
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)

    def generate_full_output(
        self, file_summaries: Dict[str, str], interface_descriptions: Dict[str, str]
    ) -> str:
        """
        Create llms-full.txt content.

        Args:
            file_summaries (Dict[str, str]): Dictionary of file paths to summaries.
            interface_descriptions (Dict[str, str]): Dictionary of file paths to interface descriptions.

        Returns:
            str: Content for llms-full.txt.
        """
        self.logger.info("Generating full output content...")

        # Start with a header
        content = "# Repository Analysis - Detailed Report\n\n"

        # Add file summaries
        content += "## File Summaries\n\n"
        for file_path, summary in file_summaries.items():
            content += summary

        # Add interface descriptions if any
        if interface_descriptions:
            content += "## Inferred Interfaces\n\n"
            for file_path, description in interface_descriptions.items():
                content += description

        return content

    def write_output_files(
        self, full_content: str, summary_content: str
    ) -> Dict[str, str]:
        """
        Write files to specified directory.

        Args:
            full_content (str): Content for llms-full.txt.
            summary_content (str): Content for llms.txt.

        Returns:
            Dict[str, str]: Dictionary of output file paths.
        """
        self.logger.info(f"Writing output files to {self.output_dir}...")

        # Ensure output directory exists
        output_path = Path(self.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Define output file paths
        full_output_path = output_path / "llms-full.txt"
        summary_output_path = output_path / "llms.txt"

        # Write llms-full.txt
        try:
            with open(full_output_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            self.logger.info(f"Wrote detailed analysis to {full_output_path}")
        except Exception as e:
            self.logger.error(f"Error writing llms-full.txt: {str(e)}")
            raise

        # Write llms.txt
        try:
            with open(summary_output_path, "w", encoding="utf-8") as f:
                f.write(summary_content)
            self.logger.info(f"Wrote summary analysis to {summary_output_path}")
        except Exception as e:
            self.logger.error(f"Error writing llms.txt: {str(e)}")
            raise

        return {
            "full_output": str(full_output_path),
            "summary_output": str(summary_output_path),
        }
