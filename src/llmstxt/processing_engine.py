"""
Processing Engine for the AI-Powered Repository Analyzer with mock testing support.

This module handles document loading, parsing, and summarization using LlamaIndex.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from llama_index.core.schema import Document, NodeWithScore

from llama_index.core.readers import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.node_parser import CodeSplitter
from llama_index.core.response_synthesizers import (
    get_response_synthesizer, # Will be used via LLMService
    ResponseMode,
)
# from llama_index.llms.openai import OpenAI # No longer directly used

from llmstxt.prompts import (
    MARKDOWN_SUMMARY_PROMPT,
    PYTHON_CODE_SUMMARY_PROMPT,
    JS_TS_CODE_SUMMARY_PROMPT,
    GENERIC_CODE_SUMMARY_PROMPT,
)

# Import LLMService
from llmstxt.llm_service import LLMService


class ProcessingEngine:
    """
    Core analysis component that processes repository files and generates summaries.
    """

    def __init__(self, llm_service: LLMService, max_file_size_kb: int = 256):
        """
        Initialize the processing engine.

        Args:
            llm_service (LLMService): The LLM service instance.
            max_file_size_kb (int): Maximum file size in KB to process.
        """
        self.max_file_size_kb = max_file_size_kb
        self.logger = logging.getLogger(__name__)
        self.llm_service = llm_service # Store the service
        # self.use_mock = use_mock # No longer needed here directly
        # LLM initialization is removed from here

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
        all_docs = []
        processed_docs = [] # Renamed 'documents' to 'processed_docs' to avoid confusion

        # Check if directory exists
        repo_dir = Path(repo_path)
        if not repo_dir.exists() or not repo_dir.is_dir():
            self.logger.error(
                f"Repository path does not exist or is not a directory: {repo_path}"
            )
            raise ValueError(f"Invalid repository path: {repo_path}")

        # Attempt to use SimpleDirectoryReader first
        sdr_failed_or_empty = False
        try:
            self.logger.info("Attempting to load documents with SimpleDirectoryReader...")
            # SimpleDirectoryReader requires string extensions without leading dots
            sdr_extensions = [ext.lstrip(".") for ext in extensions if ext]
            reader = SimpleDirectoryReader(
                input_dir=str(repo_path), # Ensure input_dir is a string
                required_exts=sdr_extensions if sdr_extensions else None, # Pass None if no specific extensions
                recursive=True,
                exclude=exclusions, # SimpleDirectoryReader handles gitignore-style patterns
                file_metadata=lambda filename: {"file_path": filename},
            )
            all_docs = reader.load_data()
            self.logger.info(f"SimpleDirectoryReader loaded {len(all_docs)} documents.")

            # Check if SDR returned empty results when files were expected
            if not all_docs:
                # Heuristic: Check if there are any files matching extensions in the repo path
                has_matching_files = any(
                    any(f.match(f"*{ext}") for ext in extensions)
                    for f in repo_dir.rglob("*") if f.is_file()
                )
                if has_matching_files:
                    self.logger.warning(
                        "SimpleDirectoryReader loaded 0 documents, but matching files appear to exist."
                    )
                    sdr_failed_or_empty = True
                else:
                    self.logger.info("SimpleDirectoryReader loaded 0 documents, and no matching files were found by heuristic.")

        except Exception as e:
            self.logger.warning(
                f"SimpleDirectoryReader failed with error: {str(e)}. Will attempt fallback."
            )
            sdr_failed_or_empty = True
            all_docs = [] # Ensure all_docs is empty for fallback logic

        # Fallback to CustomFileReader if SimpleDirectoryReader failed or returned empty unexpectedly
        if sdr_failed_or_empty:
            self.logger.warning("Falling back to CustomFileReader.")
            try:
                from llmstxt.custom_file_reader import CustomFileReader
                custom_reader = CustomFileReader()
                all_docs = custom_reader.load_data(
                    repo_path=str(repo_path), # Ensure repo_path is a string
                    extensions=extensions, # CustomFileReader handles extensions with leading dots
                    exclusions=exclusions,
                    max_file_size_kb=self.max_file_size_kb,
                    gitignore_handler=gitignore_handler, # Pass the actual handler
                )
                self.logger.info(f"CustomFileReader loaded {len(all_docs)} documents.")
            except Exception as e_custom:
                self.logger.error(f"CustomFileReader also failed: {str(e_custom)}")
                # If CustomFileReader also fails, re-raise the exception or handle as appropriate
                raise  # Or return empty list: return []

        # Filter documents by size and content (common post-processing for both readers)
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

                processed_docs.append(doc)

            self.logger.info(f"Successfully processed and filtered {len(processed_docs)} documents.")
            return processed_docs

        except Exception as e: # Catching outer scope exceptions during loading/filtering
            self.logger.error(f"An error occurred during the document loading process: {str(e)}")
            raise # Re-raise the exception to be caught by the main error handler

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

            # Create response synthesizer using LLMService
            response_synthesizer = self.llm_service.get_response_synthesizer(
                response_mode=ResponseMode.TREE_SUMMARIZE,
                prompt_template=prompt_template
            )

            # Convert nodes to NodeWithScore
            nodes_with_score = [NodeWithScore(node=node, score=1.0) for node in nodes]

            # Generate summary using wrapped nodes
            summary = response_synthesizer.synthesize(query="", nodes=nodes_with_score)

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
            doc = Document(
                text=truncated_content, metadata={"file_path": "llms-full.txt"}
            )
            nodes = self.sentence_splitter.get_nodes_from_documents([doc])

            # Create response synthesizer with overall summary prompt
            from llmstxt.prompts import OVERALL_SUMMARY_PROMPT

            response_synthesizer = self.llm_service.get_response_synthesizer(
                response_mode=ResponseMode.TREE_SUMMARIZE,
                prompt_template=OVERALL_SUMMARY_PROMPT
            )

            # Convert nodes to NodeWithScore
            nodes_with_score = [NodeWithScore(node=node, score=1.0) for node in nodes]

            # Generate summary using wrapped nodes
            summary = response_synthesizer.synthesize(query="", nodes=nodes_with_score)

            return f"# Repository Summary\n\n{summary.response}\n"

        except Exception as e:
            self.logger.error(f"Error generating repository summary: {str(e)}")
            return "# Repository Summary\n\n*Error generating summary*\n"
