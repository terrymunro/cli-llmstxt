"""
Utility module for logging configuration.

This module configures the logging system for the repository analyzer.
"""

import logging
import sys


def setup_logging(level=logging.INFO):
    """
    Configure logging for the repository analyzer.

    Args:
        level (int): Logging level (default: logging.INFO)
    """
    # Create logger
    logger = logging.getLogger("llmstxt")
    logger.setLevel(level)

    # Create console handler and set level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add formatter to console handler
    console_handler.setFormatter(formatter)

    # Add console handler to logger
    logger.addHandler(console_handler)

    return logger
