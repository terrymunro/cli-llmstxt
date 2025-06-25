"""
Interface Analysis Module for the AI-Powered Repository Analyzer with mock testing support.

This module analyzes code to infer public interfaces when documentation is insufficient.
"""

import logging
from typing import List, Optional

from llama_index.core.response_synthesizers import (
    get_response_synthesizer,
    ResponseMode,
)
# get_response_synthesizer will be used via LLMService

from llmstxt.prompts import (
    FLASK_API_INFERENCE_PROMPT,
    FASTAPI_API_INFERENCE_PROMPT,
    PYTHON_LIBRARY_INFERENCE_PROMPT,
)

# Import LLMService
from llmstxt.llm_service import LLMService


class InterfaceAnalysis:
    """
    Analyzes code to infer public interfaces when documentation is insufficient.
    """

    def __init__(self, llm_service: LLMService):
        """
        Initialize the interface analysis module.

        Args:
            llm_service (LLMService): The LLM service instance.
        """
        self.llm_service = llm_service # Store the service
        # self.llm = llm # No longer needed here directly
        # self.use_mock = use_mock # No longer needed here directly
        self.logger = logging.getLogger(__name__)

    def should_analyze_interface(
        self, doc_quality: Optional[str] = None, trigger_flag: bool = False
    ) -> bool:
        """
        Determine if interface analysis is needed.

        Args:
            doc_quality (Optional[str]): Quality assessment of documentation.
            trigger_flag (bool): Flag to force interface analysis.

        Returns:
            bool: True if interface analysis should be performed.
        """
        # If trigger flag is set, always analyze
        if trigger_flag:
            return True

        # For V1, we'll use a simple heuristic
        # In future versions, this could be enhanced with LLM-based assessment
        if doc_quality and "insufficient" in doc_quality.lower():
            return True

        # For now, default to analyzing interfaces for Python files
        return True

    def analyze_code_interface(self, nodes: List, file_path: str) -> Optional[str]:
        """
        Identify public interfaces in code.

        Args:
            nodes (List): List of code nodes.
            file_path (str): Path to the file.

        Returns:
            Optional[str]: Description of inferred interfaces, or None if not applicable.
        """
        self.logger.info(f"Analyzing code interface for: {file_path}")

        # Skip if no nodes
        if not nodes:
            return None

        try:
            # Determine file type and appropriate analysis
            if file_path.endswith(".py"):
                # Check for Flask patterns
                if self._contains_flask_patterns(nodes):
                    return self._extract_flask_api_endpoints(nodes, file_path)

                # Check for FastAPI patterns
                elif self._contains_fastapi_patterns(nodes):
                    return self._extract_fastapi_api_endpoints(nodes, file_path)

                # Default to Python library analysis
                else:
                    return self._extract_python_public_interface(nodes, file_path)

            # For V1, we focus on Python files
            # Future versions could add support for other languages
            return None

        except Exception as e:
            self.logger.error(
                f"Error analyzing code interface for {file_path}: {str(e)}"
            )
            return None

    def _contains_flask_patterns(self, nodes: List) -> bool:
        """
        Check if nodes contain Flask patterns.

        Args:
            nodes (List): List of code nodes.

        Returns:
            bool: True if Flask patterns are detected.
        """
        # Look for Flask imports and route decorators
        for node in nodes:
            text = node.text.lower()
            if "from flask import" in text or "import flask" in text:
                if "@app.route" in text or "@blueprint.route" in text:
                    return True
        return False

    def _contains_fastapi_patterns(self, nodes: List) -> bool:
        """
        Check if nodes contain FastAPI patterns.

        Args:
            nodes (List): List of code nodes.

        Returns:
            bool: True if FastAPI patterns are detected.
        """
        # Look for FastAPI imports and endpoint decorators
        for node in nodes:
            text = node.text.lower()
            if "from fastapi import" in text or "import fastapi" in text:
                if "@app." in text and any(
                    method in text
                    for method in ["get", "post", "put", "delete", "patch"]
                ):
                    return True
        return False

    def _extract_flask_api_endpoints(self, nodes: List, file_path: str) -> str:
        """
        Extract API endpoints from Flask code.

        Args:
            nodes (List): List of code nodes.
            file_path (str): Path to the file.

        Returns:
            str: Description of inferred Flask API endpoints.
        """
        self.logger.info(f"Extracting Flask API endpoints from: {file_path}")

        # Create response synthesizer using LLMService
        response_synthesizer = self.llm_service.get_response_synthesizer(
            response_mode=ResponseMode.TREE_SUMMARIZE,
            prompt_template=FLASK_API_INFERENCE_PROMPT
        )

        # Generate interface description
        interface = response_synthesizer.synthesize(query="", nodes=nodes)

        return (
            f"### ⚠️ Inferred Flask API Endpoints for {file_path}\n\n"
            f"*The following interface was inferred from code structure and patterns. "
            f"Accuracy may vary and verification is recommended.*\n\n"
            f"{interface.response}\n\n"
        )

    def _extract_fastapi_api_endpoints(self, nodes: List, file_path: str) -> str:
        """
        Extract API endpoints from FastAPI code.

        Args:
            nodes (List): List of code nodes.
            file_path (str): Path to the file.

        Returns:
            str: Description of inferred FastAPI API endpoints.
        """
        self.logger.info(f"Extracting FastAPI API endpoints from: {file_path}")

        # Create response synthesizer using LLMService
        response_synthesizer = self.llm_service.get_response_synthesizer(
            response_mode=ResponseMode.TREE_SUMMARIZE,
            prompt_template=FASTAPI_API_INFERENCE_PROMPT
        )

        # Generate interface description
        interface = response_synthesizer.synthesize(query="", nodes=nodes)

        return (
            f"### ⚠️ Inferred FastAPI API Endpoints for {file_path}\n\n"
            f"*The following interface was inferred from code structure and patterns. "
            f"Accuracy may vary and verification is recommended.*\n\n"
            f"{interface.response}\n\n"
        )

    def _extract_python_public_interface(self, nodes: List, file_path: str) -> str:
        """
        Extract public functions/classes from Python library code.

        Args:
            nodes (List): List of code nodes.
            file_path (str): Path to the file.

        Returns:
            str: Description of inferred Python public interface.
        """
        self.logger.info(f"Extracting Python public interface from: {file_path}")

        # Create response synthesizer using LLMService
        response_synthesizer = self.llm_service.get_response_synthesizer(
            response_mode=ResponseMode.TREE_SUMMARIZE,
            prompt_template=PYTHON_LIBRARY_INFERENCE_PROMPT
        )

        # Generate interface description
        interface = response_synthesizer.synthesize(query="", nodes=nodes)

        return (
            f"### ⚠️ Inferred Python Public Interface for {file_path}\n\n"
            f"*The following interface was inferred from code structure and patterns. "
            f"Accuracy may vary and verification is recommended.*\n\n"
            f"{interface.response}\n\n"
        )
