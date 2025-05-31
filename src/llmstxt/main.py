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


def main():
    """
    Main entry point for the repository analyzer.
    """
    # Set up logging
    logger = setup_logging()

    try:
        load_dotenv()

        use_mock = False
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning(
                "OPENAI_API_KEY environment variable is not set. Using mock LLM for testing."
            )
            use_mock = True

        args = parse_arguments()

        is_valid, error_message = validate_arguments(args)
        if not is_valid:
            logger.error(f"Invalid arguments: {error_message}")
            sys.exit(1)

        repo_acquisition = RepositoryAcquisition()
        try:
            repo_path = repo_acquisition.acquire_repository(args.repo_specifier)
            logger.info(f"Using repository at: {repo_path}")
        except ValueError as e:
            logger.error(f"Repository acquisition failed: {str(e)}")
            sys.exit(1)

        # Parse extensions
        extensions = [ext.strip() for ext in args.code_extensions.split(",")]
        logger.info(f"Processing files with extensions: {extensions}")

        # Initialize gitignore handler if requested
        gitignore_handler = None
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
            except Exception as e:
                logger.warning("Failed to initialize gitignore handler: %s", str(e))
                gitignore_handler = None
        else:
            logger.info("GitIgnore support disabled")

        # Define exclusion patterns
        exclusions = [
            "**/.*",
            "**/node_modules/**",
            "**/venv/**",
            "**/__pycache__/**",
            "**/build/**",
            "**/dist/**",
            "**/target/**",
            "**/*.lock",
            "**/*.log",
        ]

        # Add gitignore patterns to exclusions if available
        if gitignore_handler:
            gitignore_patterns = gitignore_handler.get_ignore_patterns_for_exclusions()
            exclusions.extend(gitignore_patterns)
            logger.info(
                "Added %d gitignore patterns to exclusions", len(gitignore_patterns)
            )

        # Initialize processing engine
        processing_engine = ProcessingEngine(
            max_file_size_kb=args.max_file_size_kb, use_mock=use_mock
        )

        # Load documents
        try:
            documents = processing_engine.load_documents(
                repo_path, extensions, exclusions, gitignore_handler
            )
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
            repo_acquisition.cleanup()
            sys.exit(1)

        # Initialize interface analysis
        interface_analysis = InterfaceAnalysis(
            llm=processing_engine.llm, use_mock=use_mock
        )

        # Process documents
        file_summaries = {}
        interface_descriptions = {}

        for document in documents:
            file_path = document.metadata.get("file_path", "")

            try:
                # Parse document into nodes
                nodes, file_type = processing_engine.parse_document(document)

                # Generate file summary
                summary = processing_engine.summarize_file(nodes, file_type, file_path)
                file_summaries[file_path] = summary

                # Analyze code interface if applicable
                if args.trigger_interface_analysis and file_path.endswith(".py"):
                    interface = interface_analysis.analyze_code_interface(
                        nodes, file_path
                    )
                    if interface:
                        interface_descriptions[file_path] = interface

            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                continue

        output_generator = OutputGenerator(args.output_dir)

        full_content = output_generator.generate_full_output(
            file_summaries, interface_descriptions
        )

        max_chars = args.max_overall_summary_input_chars
        summary_content = processing_engine.summarize_repository(
            full_content, max_chars
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

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

    finally:
        # Clean up temporary directory if created
        if "repo_acquisition" in locals():
            repo_acquisition.cleanup()


if __name__ == "__main__":
    main()
