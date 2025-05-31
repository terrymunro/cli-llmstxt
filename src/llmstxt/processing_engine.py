"""
Processing Engine for the AI-Powered Repository Analyzer with mock testing support.

This module handles document loading, parsing, and summarization using LlamaIndex.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple

from llama_index.core.readers import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.node_parser import CodeSplitter
from llama_index.core.response_synthesizers import (
    get_response_synthesizer,
    ResponseMode,
)
from llama_index.llms.openai import OpenAI

from llmstxt.prompts import (
    MARKDOWN_SUMMARY_PROMPT,
    PYTHON_CODE_SUMMARY_PROMPT,
    JS_TS_CODE_SUMMARY_PROMPT,
    GENERIC_CODE_SUMMARY_PROMPT,
)


class ProcessingEngine:
    """
    Core analysis component that processes repository files and generates summaries.
    """

    def __init__(self, max_file_size_kb: int = 256, use_mock: bool = False):
        """
        Initialize the processing engine.

        Args:
            max_file_size_kb (int): Maximum file size in KB to process.
            use_mock (bool): Whether to use mock LLM for testing.
        """
        self.max_file_size_kb = max_file_size_kb
        self.logger = logging.getLogger(__name__)
        self.use_mock = use_mock

        # Initialize LLM
        if use_mock:
            from llmstxt.mock_llm import MockLLM

            self.llm = MockLLM(model="gpt-4o-mini")
            self.logger.info("Using mock LLM for testing")
        else:
            self.llm = OpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

        # Initialize node parsers
        self.markdown_parser = MarkdownNodeParser()
        self.sentence_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

        # Try to initialize code splitters, fall back to sentence splitter if tree_sitter is not available
        try:
            self.code_splitter_py = CodeSplitter(
                language="python",
                chunk_lines=40,
                chunk_lines_overlap=15,
                max_chars=1500,
            )
            self.code_splitter_js = CodeSplitter(
                language="javascript",
                chunk_lines=40,
                chunk_lines_overlap=15,
                max_chars=1500,
            )
            self.has_code_splitter = True
        except ImportError:
            self.logger.warning(
                "tree_sitter module not found. Using sentence splitter for code files."
            )
            self.has_code_splitter = False

    def load_documents(
        self,
        repo_path: str,
        extensions: List[str],
        exclusions: List[str],
        gitignore_handler=None,
    ) -> List[Dict]:
        """
        Load documents from the repository.

        Args:
            repo_path (str): Path to the repository.
            extensions (List[str]): List of file extensions to process.
            exclusions (List[str]): List of patterns to exclude.
            gitignore_handler: Optional handler for .gitignore files.

        Returns:
            List[Dict]: List of loaded documents with metadata.
        """
        self.logger.info(f"Loading documents from {repo_path}...")

        # Convert extensions to format required by SimpleDirectoryReader
        # Make sure to remove the leading dot and handle both formats (.py and py)
        required_exts = [ext.lstrip(".") for ext in extensions]
        self.logger.info(f"Using file extensions: {required_exts}")

        try:
            # Create a list to store documents
            documents = []

            # Check if directory exists and has files
            repo_dir = Path(repo_path)
            if not repo_dir.exists() or not repo_dir.is_dir():
                self.logger.error(
                    f"Repository path does not exist or is not a directory: {repo_path}"
                )
                raise ValueError(f"Invalid repository path: {repo_path}")

            # Log files in directory for debugging
            self.logger.info("Files in repository directory:")
            for file_path in repo_dir.glob("**/*"):
                if file_path.is_file():
                    self.logger.info(f"  Found file: {file_path}")

            # Try to use SimpleDirectoryReader, fall back to custom reader if not available
            try:
                reader = SimpleDirectoryReader(
                    input_dir=repo_path,
                    recursive=True,
                    exclude=exclusions,
                    file_metadata=lambda filename: {"file_path": filename},
                )
                all_docs = reader.load_data()
            except Exception as e:
                self.logger.warning(
                    f"SimpleDirectoryReader failed: {str(e)}. Using custom file reader."
                )
                from llmstxt.custom_file_reader import CustomFileReader

                custom_reader = CustomFileReader()
                all_docs = custom_reader.load_data(
                    repo_path=repo_path,
                    extensions=extensions,
                    exclusions=exclusions,
                    max_file_size_kb=self.max_file_size_kb,
                    gitignore_handler=gitignore_handler,
                )

            # all_docs is already loaded in the try/except block above

            # Filter documents by size
            for doc in all_docs:
                file_path = doc.metadata.get("file_path", "")
                file_size_kb = os.path.getsize(file_path) / 1024

                if self.max_file_size_kb > 0 and file_size_kb > self.max_file_size_kb:
                    self.logger.warning(
                        f"Skipping file due to size limit ({file_size_kb:.2f}KB): {file_path}"
                    )
                    continue

                if not doc.text.strip():
                    self.logger.warning(f"Skipping empty file: {file_path}")
                    continue

                documents.append(doc)

            self.logger.info(f"Loaded {len(documents)} documents")
            return documents

        except Exception as e:
            self.logger.error(f"Error loading documents: {str(e)}")
            raise

    def parse_document(self, document: Dict) -> Tuple[List, str]:
        """
        Parse a document into nodes using the appropriate parser.

        Args:
            document (Dict): Document to parse.

        Returns:
            Tuple[List, str]: Tuple of (nodes, file_type).
        """
        file_path = document.metadata.get("file_path", "")
        file_ext = Path(file_path).suffix.lower()

        try:
            if file_ext == ".md":
                nodes = self.markdown_parser.get_nodes_from_documents([document])
                file_type = "markdown"
            elif file_ext == ".py" and self.has_code_splitter:
                nodes = self.code_splitter_py.get_nodes_from_documents([document])
                file_type = "python"
            elif file_ext in [".js", ".ts"] and self.has_code_splitter:
                nodes = self.code_splitter_js.get_nodes_from_documents([document])
                file_type = "javascript"
            else:
                # Use sentence splitter as fallback for all code files if code splitter is not available
                nodes = self.sentence_splitter.get_nodes_from_documents([document])
                file_type = (
                    "python"
                    if file_ext == ".py"
                    else "javascript"
                    if file_ext in [".js", ".ts"]
                    else "generic"
                )

            return nodes, file_type

        except Exception as e:
            self.logger.error(f"Error parsing document {file_path}: {str(e)}")
            # Fall back to sentence splitter
            nodes = self.sentence_splitter.get_nodes_from_documents([document])
            return nodes, "generic"

    def summarize_file(self, nodes: List, file_type: str, file_path: str) -> str:
        """
        Generate a summary for an individual file.

        Args:
            nodes (List): List of nodes from the file.
            file_type (str): Type of file (markdown, python, javascript, generic).
            file_path (str): Path to the file.

        Returns:
            str: Summary of the file.
        """
        self.logger.info(f"Summarizing file: {file_path}")

        try:
            # Select appropriate prompt template
            if file_type == "markdown":
                prompt_template = MARKDOWN_SUMMARY_PROMPT
            elif file_type == "python":
                prompt_template = PYTHON_CODE_SUMMARY_PROMPT
            elif file_type == "javascript":
                prompt_template = JS_TS_CODE_SUMMARY_PROMPT
            else:
                prompt_template = GENERIC_CODE_SUMMARY_PROMPT

            # Create response synthesizer
            if self.use_mock:
                from llmstxt.mock_llm import get_mock_response_synthesizer

                response_synthesizer = get_mock_response_synthesizer(
                    response_mode=ResponseMode.TREE_SUMMARIZE,
                    llm=self.llm,
                    prompt_template=prompt_template,
                )
            else:
                response_synthesizer = get_response_synthesizer(
                    response_mode=ResponseMode.TREE_SUMMARIZE,
                    llm=self.llm,
                )
                response_synthesizer.text_qa_template = prompt_template

            # Generate summary
            summary = response_synthesizer.synthesize(query="", nodes=nodes)

            return f"### Summary of {file_path}\n\n{summary.response}\n\n"

        except Exception as e:
            self.logger.error(f"Error summarizing file {file_path}: {str(e)}")
            return f"### Summary of {file_path}\n\n*Error generating summary: {str(e)}*\n\n"

    def summarize_repository(self, full_content: str, max_chars: int) -> str:
        """
        Generate an overall repository summary.

        Args:
            full_content (str): Content of llms-full.txt.
            max_chars (int): Maximum number of characters to use for summary.

        Returns:
            str: Overall repository summary.
        """
        self.logger.info("Generating overall repository summary...")

        try:
            # Truncate content if necessary
            if len(full_content) > max_chars:
                self.logger.info(
                    f"Truncating content from {len(full_content)} to {max_chars} characters"
                )
                truncated_content = full_content[:max_chars]
            else:
                truncated_content = full_content

            # Create nodes from truncated content
            nodes = self.sentence_splitter.get_nodes_from_documents(
                [
                    {
                        "text": truncated_content,
                        "metadata": {"file_path": "llms-full.txt"},
                    }
                ]
            )

            # Create response synthesizer with overall summary prompt
            from llmstxt.prompts import OVERALL_SUMMARY_PROMPT

            if self.use_mock:
                from llmstxt.mock_llm import get_mock_response_synthesizer

                response_synthesizer = get_mock_response_synthesizer(
                    response_mode=ResponseMode.TREE_SUMMARIZE,
                    llm=self.llm,
                    prompt_template=OVERALL_SUMMARY_PROMPT,
                )
            else:
                response_synthesizer = get_response_synthesizer(
                    response_mode=ResponseMode.TREE_SUMMARIZE,
                    llm=self.llm,
                )
                response_synthesizer.text_qa_template = OVERALL_SUMMARY_PROMPT

            # Generate summary
            summary = response_synthesizer.synthesize(query="", nodes=nodes)

            return f"# Repository Summary\n\n{summary.response}\n"

        except Exception as e:
            self.logger.error(f"Error generating repository summary: {str(e)}")
            return "# Repository Summary\n\n*Error generating summary*\n"
