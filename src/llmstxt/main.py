"""
Main entry point for the AI-Powered Repository Analyzer CLI with mock testing support.

This module ties together all components and provides the main execution flow.
"""

import os
import sys
from dotenv import load_dotenv

from llmstxt.cli import parse_arguments, validate_arguments
from llmstxt.repository import RepositoryAcquisition
from llmstxt.processing_engine import ProcessingEngine
from llmstxt.interface_analysis import InterfaceAnalysis
from llmstxt.output_generator import OutputGenerator
from llmstxt.logging_config import setup_logging
from llmstxt.gitignore_handler import GitIgnoreHandler
from src.llmstxt.config import DEFAULT_EXCLUSIONS
from src.llmstxt.llm_service import LLMService # Import LLMService


def _setup_logging_and_env():
    """Sets up logging and environment variables."""
    logger = setup_logging()
    load_dotenv()
    use_mock = False
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning(
            "OPENAI_API_KEY environment variable is not set. Using mock LLM for testing."
        )
        use_mock = True
    return logger, use_mock


def _parse_and_validate_args(logger):
    """Parses and validates command-line arguments."""
    args = parse_arguments()
    is_valid, error_message = validate_arguments(args)
    if not is_valid:
        logger.error(f"Invalid arguments: {error_message}")
        sys.exit(1)
    return args


def _acquire_repository(args, logger):
    """Acquires the repository specified by the arguments."""
    repo_acquisition = RepositoryAcquisition()
    try:
        repo_path = repo_acquisition.acquire_repository(args.repo_specifier)
        logger.info(f"Using repository at: {repo_path}")
        return repo_path, repo_acquisition
    except ValueError as e:
        logger.error(f"Repository acquisition failed: {str(e)}")
        if repo_acquisition: # Ensure cleanup if partially successful
            repo_acquisition.cleanup()
        sys.exit(1)


def _initialize_gitignore_handler(args, repo_path, logger):
    """Initializes the GitIgnoreHandler if applicable."""
    if getattr(args, "respect_gitignore", True) and not getattr(
        args, "ignore_gitignore", False
    ):
        try:
            gitignore_handler = GitIgnoreHandler(repo_path)
            stats = gitignore_handler.get_stats()
            logger.info(
                "GitIgnore handler initialized: %d total patterns from %d .gitignore files",
                stats["total_patterns"],
                stats["gitignore_files_found"],
            )
            return gitignore_handler
        except Exception as e:
            logger.warning(f"Failed to initialize gitignore handler: {str(e)}")
    else:
        logger.info("GitIgnore support disabled")
    return None


def _get_file_processing_params(args, gitignore_handler, logger):
    """Determines file extensions and exclusion patterns."""
    extensions = [ext.strip() for ext in args.code_extensions.split(",")]
    logger.info(f"Processing files with extensions: {extensions}")

    exclusions = DEFAULT_EXCLUSIONS[:]  # Use a copy
    if gitignore_handler:
        gitignore_patterns = gitignore_handler.get_ignore_patterns_for_exclusions()
        exclusions.extend(gitignore_patterns)
        logger.info(
            "Added %d gitignore patterns to exclusions", len(gitignore_patterns)
        )
    return extensions, exclusions


def _initialize_processing_services(args, use_mock, logger):
    """Initializes core processing services."""
    # Instantiate LLMService
    # TODO: Consider making model_name configurable via args if needed in the future
    llm_service = LLMService(use_mock=use_mock)
    logger.info(f"LLM Service initialized. Mock active: {llm_service.is_mock}")

    # Pass the llm_service instance to ProcessingEngine and InterfaceAnalysis
    processing_engine = ProcessingEngine(
        llm_service=llm_service,
        max_file_size_kb=args.max_file_size_kb
    )
    interface_analysis = InterfaceAnalysis(llm_service=llm_service)

    # OutputGenerator is initialized later as it depends on args.output_dir
    return processing_engine, interface_analysis


def _process_repository_documents(
    processing_engine,
    interface_analysis,
    repo_path,
    extensions,
    exclusions,
    gitignore_handler,
    args,
    logger,
):
    """Loads, processes documents, and generates summaries/interfaces."""
    try:
        documents = processing_engine.load_documents(
            repo_path, extensions, exclusions, gitignore_handler
        )
    except Exception as e:
        logger.error(f"Error loading documents: {str(e)}")
        # No repo_acquisition to cleanup here, it's handled in main
        sys.exit(1)

    file_summaries = {}
    interface_descriptions = {}

    for document in documents:
        file_path = document.metadata.get("file_path", "")
        try:
            nodes, file_type = processing_engine.parse_document(document)
            summary = processing_engine.summarize_file(nodes, file_type, file_path)
            file_summaries[file_path] = summary

            if args.trigger_interface_analysis and file_path.endswith((".py", ".ts", ".js")): # Example: common script files
                interface = interface_analysis.analyze_code_interface(
                    nodes, file_path
                )
                if interface:
                    interface_descriptions[file_path] = interface
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            continue
    return file_summaries, interface_descriptions


def _generate_and_write_outputs(
    args,
    processing_engine,
    file_summaries,
    interface_descriptions,
    logger,
    use_mock,
):
    """Generates final summaries and writes all output files."""
    output_generator = OutputGenerator(args.output_dir)
    full_content = output_generator.generate_full_output(
        file_summaries, interface_descriptions
    )
    summary_content = processing_engine.summarize_repository(
        full_content, args.max_overall_summary_input_chars
    )
    output_files = output_generator.write_output_files(
        full_content, summary_content
    )

    logger.info("Analysis complete!")
    logger.info(f"Detailed analysis: {output_files['full_output']}")
    logger.info(f"Summary analysis: {output_files['summary_output']}")

    if use_mock:
        logger.warning(
            "Note: Analysis was performed using mock LLM responses. For actual analysis, set OPENAI_API_KEY in .env file."
        )


def main():
    """
    Main entry point for the repository analyzer.
    Orchestrates the analysis process by calling helper functions.
    """
    repo_acquisition = None  # Initialize for finally block
    try:
        logger, use_mock = _setup_logging_and_env()
        args = _parse_and_validate_args(logger)
        repo_path, repo_acquisition = _acquire_repository(args, logger)

        gitignore_handler = _initialize_gitignore_handler(args, repo_path, logger)
        extensions, exclusions = _get_file_processing_params(
            args, gitignore_handler, logger
        )
        processing_engine, interface_analysis = _initialize_processing_services(
            args, use_mock, logger
        )

        file_summaries, interface_descriptions = _process_repository_documents(
            processing_engine,
            interface_analysis,
            repo_path,
            extensions,
            exclusions,
            gitignore_handler,
            args,
            logger,
        )

        _generate_and_write_outputs(
            args,
            processing_engine,
            file_summaries,
            interface_descriptions,
            logger,
            use_mock,
        )

    except Exception as e:
        # Fallback for any unhandled exceptions in helper functions leading to SystemExit
        if "logger" not in locals(): # If logger setup failed
            logger = setup_logging() # Basic logger
        logger.error(f"An unexpected error occurred in main: {str(e)}")
        sys.exit(1)
    finally:
        if repo_acquisition:
            repo_acquisition.cleanup()


if __name__ == "__main__":
    main()
