# AI-Powered Repository Analyzer CLI Architecture

## 1. System Overview

The AI-Powered Repository Analyzer CLI is a command-line tool that leverages LlamaIndex and LLMs to analyze and summarize software repositories. It processes both documentation and source code, with a special focus on inferring public interfaces when documentation is sparse.

## 2. High-Level Architecture

The system consists of the following major components:

1. **CLI Interface**: Handles command-line argument parsing and user interaction
2. **Repository Acquisition Module**: Manages repository cloning and local path handling
3. **LlamaIndex Processing Engine**: Core analysis component with several sub-modules
4. **Code Interface Analysis Module**: Specialized component for inferring public interfaces
5. **Output Generation Module**: Formats and writes output files
6. **GitIgnore Support Module**: Excludes files matching .gitignore patterns

## 3. Component Details

### 3.1 CLI Interface

**Purpose**: Parse command-line arguments and provide user feedback during processing.

**Implementation**:

- Uses Python's `argparse` library
- Handles all specified CLI parameters:
  - `repo_specifier`: Path to local repository or GitHub URL
  - `--code_extensions`: Comma-separated list of file extensions to process
  - `--output_dir`: Directory to save output files
  - `--max_file_size_kb`: Maximum file size in KB to process
  - `--max_overall_summary_input_chars`: Max characters from llms-full.txt for final summary
  - `--trigger_interface_analysis`: Force interface analysis even if docs seem sufficient
  - `--respect_gitignore`: Respect .gitignore files when processing repository (default: True)
  - `--ignore_gitignore`: Ignore .gitignore files and process all files matching extensions
  - `--help`: Display help information

**Key Functions**:

- `parse_arguments()`: Process command-line arguments
- `validate_arguments()`: Ensure arguments are valid
- `display_progress()`: Show processing status to user

### 3.2 Repository Acquisition Module

**Purpose**: Handle repository access, whether local or remote.

**Implementation**:

- Uses `GitPython` for cloning remote repositories
- Uses `pathlib` for local file system operations
- Manages temporary directories for cloned repositories

**Key Functions**:

- `acquire_repository(repo_specifier)`: Determine if input is URL or local path
- `clone_repository(url)`: Clone GitHub repository to temporary directory
- `validate_local_path(path)`: Ensure local path exists and is a valid repository
- `cleanup_temp_directory()`: Remove temporary directories after processing

### 3.3 LlamaIndex Processing Engine

**Purpose**: Core analysis component that processes repository files and generates summaries.

**Implementation**:

- Uses LlamaIndex components for document loading, parsing, and summarization
- Configures appropriate node parsers based on file types
- Manages LLM interaction for summarization tasks

**Sub-components**:

#### 3.3.1 Document Loading

- Uses `SimpleDirectoryReader` to load files from repository
- Applies file extension filters and exclusion rules
- Respects .gitignore files for automatic exclusion of ignored files (configurable)
- Respects maximum file size limits

#### 3.3.2 Node Parsing

- `CodeSplitter`: For source code files
- `MarkdownNodeParser`: For Markdown documentation
- `SentenceSplitter`: Fallback for other text files

#### 3.3.3 LLM Abstraction

- Manages communication with OpenAI API
- Handles API key integration and request formatting

#### 3.3.4 Summarization

- File-level summarization with custom prompts
- Repository-level summarization for final output

**Key Functions**:

- `load_documents(repo_path, extensions, exclusions, max_size)`: Load repository files
- `parse_documents(documents)`: Convert documents to nodes
- `summarize_file(nodes, file_type)`: Generate summary for individual file
- `summarize_repository(summaries)`: Generate overall repository summary

### 3.4 Code Interface Analysis Module

**Purpose**: Analyze code to infer public interfaces when documentation is insufficient.

**Implementation**:

- Uses LlamaIndex's query capabilities over code nodes
- Employs specialized prompts for different code patterns
- Focuses on Python (Flask, FastAPI, general library patterns) for V1

**Key Functions**:

- `should_analyze_interface(doc_quality, trigger_flag)`: Determine if interface analysis is needed
- `analyze_code_interface(code_nodes, file_type)`: Identify public interfaces in code
- `extract_api_endpoints(code_nodes)`: Find API endpoints in web frameworks
- `extract_public_functions(code_nodes)`: Identify public functions/classes in libraries

### 3.5 GitIgnore Support Module

**Purpose**: Automatically exclude files that match .gitignore patterns from processing and indexing.

**Implementation**:

- `GitIgnoreHandler` class that parses .gitignore files from repository root and subdirectories
- Implements gitignore-compliant pattern matching including:
  - Directory patterns (`build/`, `__pycache__/`)
  - File extension patterns (`*.log`, `*.pyc`)
  - Negation patterns (`!important.log`)
  - Recursive wildcard patterns (`**/*.pyc`)
- Integrates with existing file exclusion system

**Key Functions**:

- `_parse_gitignore_files(repo_path)`: Recursively find and parse all .gitignore files
- `should_ignore(file_path)`: Determine if a file should be excluded based on gitignore rules
- `_matches_pattern(file_path, pattern)`: Match files against gitignore patterns
- `get_ignore_patterns_for_exclusions()`: Convert gitignore patterns for legacy exclusion systems

**CLI Options**:

- `--respect_gitignore`: Enable gitignore support (default: True)
- `--ignore_gitignore`: Disable gitignore support and process all files matching extensions

### 3.6 Output Generation Module

**Purpose**: Format and write output files with analysis results.

**Implementation**:

- Standard Python file I/O operations
- UTF-8 encoding for all output files

**Key Functions**:

- `generate_full_output(file_summaries, interface_descriptions)`: Create llms-full.txt content
- `generate_summary_output(full_content)`: Create llms.txt content
- `write_output_files(full_content, summary_content, output_dir)`: Write files to specified directory

## 4. Data Flow

1. User provides repository specifier and options via command line
2. CLI Interface parses and validates arguments
3. Repository Acquisition Module:
   - If URL: Clones repository to temporary directory
   - If local path: Validates path exists
4. LlamaIndex Processing Engine:
   - Loads documents from repository path
   - Parses documents into nodes
   - For each document:
     - Applies appropriate node parser
     - Generates summary using LLM
     - Stores summary
5. Code Interface Analysis Module (if triggered):
   - For relevant code files:
     - Analyzes code structure
     - Identifies potential public interfaces
     - Generates interface descriptions
     - Marks descriptions as inferred
6. Output Generation Module:
   - Combines file summaries and interface descriptions into llms-full.txt
   - Generates high-level repository summary as llms.txt
   - Writes both files to output directory
7. Repository Acquisition Module:
   - Cleans up temporary directory if created

## 5. Error Handling & Logging

- Comprehensive try-except blocks for all major operations
- Graceful handling of common errors:
  - Repository not found
  - API key missing
  - File reading/writing issues
  - LLM API errors
- Logging at different levels:
  - INFO: Progress updates
  - WARNING: Skipped files
  - ERROR: Operation failures

## 6. Configuration Management

- Environment variables loaded from .env file using python-dotenv
- OPENAI_API_KEY stored securely, not passed via command line
- Default values for all configurable parameters

## 7. File Structure

```
llmstxt/
├── __init__.py
├── main.py                  # Entry point
├── cli.py                   # CLI Interface
├── repository.py            # Repository Acquisition Module
├── processing_engine.py     # LlamaIndex Processing Engine
├── interface_analysis.py    # Code Interface Analysis Module
├── output_generator.py      # Output Generation Module
├── logging_config.py        # Logging configuration
├── prompts.py               # LLM prompt templates
├── mock_llm.py              # Mock LLM for testing
├── custom_file_reader.py    # Custom file reader fallback
├── utils.py                 # Miscellaneous utilities
└── app.py                   # Example Flask app for testing
```

## 8. Dependencies

- Python 3.13+
- LlamaIndex (core components)
- GitPython
- python-dotenv
- OpenAI API (or other LLM provider)
- Standard library: argparse, pathlib, logging, tempfile, shutil
