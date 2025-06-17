# src/llmstxt/config.py
"""Configuration settings for the llmstxt application."""

import os
from pathlib import Path

# General Configuration
DEFAULT_OUTPUT_DIR = Path(".")
DEFAULT_CODE_EXTENSIONS = ".py,.js,.ts,.java,.go,.rb,.php,.cs,.c,.cpp,.h,.hpp,.rs,.kt,.scala,.md"
MAX_FILE_SIZE_KB = 256  # Maximum file size in KB to process. 0 for no limit.
MAX_OVERALL_SUMMARY_INPUT_CHARS = 150000  # Max characters from llms-full.txt for final summary.

# LLM Configuration
# Ensure OPENAI_API_KEY is loaded from .env or environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL_NAME = "gpt-4o-mini"

# Logging Configuration
LOG_LEVEL = "INFO" # e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL

# Exclusion patterns for files and directories
DEFAULT_EXCLUSIONS = [
    "**/.*",  # Hidden files and directories
    "**/node_modules/**",
    "**/venv/**",
    "**/__pycache__/**",
    "**/build/**",
    "**/dist/**",
    "**/target/**",
    "**/*.lock",
    "**/*.log",
    # Add any other common patterns to exclude
]
