"""
CLI Interface for the AI-Powered Repository Analyzer.

This module handles command-line argument parsing and validation.
"""

import argparse
import os
from pathlib import Path

from src.llmstxt.config import (
    DEFAULT_CODE_EXTENSIONS,
    DEFAULT_OUTPUT_DIR,
    MAX_FILE_SIZE_KB,
    MAX_OVERALL_SUMMARY_INPUT_CHARS,
)


def parse_arguments():
    """
    Parse command-line arguments for the repository analyzer.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="AI-Powered Repository Analyzer CLI (LlamaIndex Edition)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required positional argument
    parser.add_argument(
        "repo_specifier", help="Path to the local repository or GitHub URL."
    )

    # Optional arguments
    parser.add_argument(
        "--code_extensions",
        default=DEFAULT_CODE_EXTENSIONS,
        help="Comma-separated list of file extensions to process.",
    )

    parser.add_argument(
        "--output_dir",
        default=DEFAULT_OUTPUT_DIR,
        type=Path,
        help="Directory to save output files.",
    )

    parser.add_argument(
        "--max_file_size_kb",
        type=int,
        default=MAX_FILE_SIZE_KB,
        help="Maximum file size in KB to process. 0 for no limit.",
    )

    parser.add_argument(
        "--max_overall_summary_input_chars",
        type=int,
        default=MAX_OVERALL_SUMMARY_INPUT_CHARS,
        help="Max characters from llms-full.txt for final summary.",
    )

    parser.add_argument(
        "--trigger_interface_analysis",
        action="store_true",
        help="Force interface analysis even if docs seem sufficient.",
    )

    parser.add_argument(
        "--respect_gitignore",
        action="store_true",
        default=True,
        help="Respect .gitignore files when processing repository (default: True).",
    )

    parser.add_argument(
        "--ignore_gitignore",
        action="store_true",
        help="Ignore .gitignore files and process all files matching extensions.",
    )

    return parser.parse_args()


def validate_arguments(args):
    """
    Validate the parsed command-line arguments.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if output directory exists or can be created
    output_dir = Path(args.output_dir)
    if not output_dir.exists():
        try:
            output_dir.mkdir(parents=True)
        except Exception as e:
            return False, f"Error creating output directory: {str(e)}"
    elif not output_dir.is_dir():
        return False, f"Output path exists but is not a directory: {args.output_dir}"

    # Check if max_file_size_kb is non-negative
    if args.max_file_size_kb < 0:
        return False, "max_file_size_kb must be non-negative"

    # Check if max_overall_summary_input_chars is positive
    if args.max_overall_summary_input_chars <= 0:
        return False, "max_overall_summary_input_chars must be positive"

    # Handle mutually exclusive gitignore options
    if hasattr(args, "ignore_gitignore") and args.ignore_gitignore:
        args.respect_gitignore = False

    # Check if OPENAI_API_KEY is set, but allow execution in mock mode
    if not os.getenv("OPENAI_API_KEY"):
        # We'll warn about this in main.py but not block execution
        pass

    return True, ""
