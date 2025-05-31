"""
Prompt templates for the AI-Powered Repository Analyzer.

This module contains the prompt templates used for LLM interactions.
"""

from llama_index.core.prompts import PromptTemplate


# Prompt for summarizing a Markdown file
MARKDOWN_SUMMARY_PROMPT = PromptTemplate(
    """Summarize this Markdown documentation, highlighting project goals, key features, setup/usage, and any architectural or contribution info. 
Note if it clearly explains the project's interfaces. Format as Markdown.

Documentation content:
{text}

Summary:"""
)

# Prompt for summarizing a Python code file
PYTHON_CODE_SUMMARY_PROMPT = PromptTemplate(
    """Summarize this Python code, focusing on its main role, key components (classes/functions), and potential interactions. 
If it defines a public API or library functions, describe them including inputs/outputs. Format as Markdown.

Code content:
{text}

Summary:"""
)

# Prompt for summarizing a JavaScript/TypeScript code file
JS_TS_CODE_SUMMARY_PROMPT = PromptTemplate(
    """Summarize this JavaScript/TypeScript code, focusing on its main role, key components (functions/classes), and potential interactions. 
If it defines a public API or library functions, describe them including inputs/outputs. Format as Markdown.

Code content:
{text}

Summary:"""
)

# Prompt for summarizing other code files
GENERIC_CODE_SUMMARY_PROMPT = PromptTemplate(
    """Summarize this code, focusing on its main role, key components, and potential interactions. 
If it defines a public API or library functions, describe them including inputs/outputs. Format as Markdown.

Code content:
{text}

Summary:"""
)

# Prompt for inferring Flask API endpoints
FLASK_API_INFERENCE_PROMPT = PromptTemplate(
    """Analyze this Python/Flask code for @app.route or @blueprint.route definitions. 
For each endpoint, identify:
1. HTTP method(s)
2. URL path
3. Function parameters and their types
4. Return value or response format
5. Purpose of the endpoint

Format as a Markdown list with clear headers for each endpoint.

Code content:
{text}

Inferred API Endpoints:"""
)

# Prompt for inferring FastAPI endpoints
FASTAPI_API_INFERENCE_PROMPT = PromptTemplate(
    """Analyze this Python/FastAPI code for API endpoint definitions (@app.get, @app.post, etc. or @router decorators). 
For each endpoint, identify:
1. HTTP method
2. URL path
3. Path/query parameters and their types
4. Request body structure if applicable
5. Response model and status codes
6. Purpose of the endpoint

Format as a Markdown list with clear headers for each endpoint.

Code content:
{text}

Inferred API Endpoints:"""
)

# Prompt for inferring public functions/classes in a Python library
PYTHON_LIBRARY_INFERENCE_PROMPT = PromptTemplate(
    """Analyze this Python code to identify public functions, classes, and methods (those not starting with underscore).
For each public element, identify:
1. Name and signature (parameters with types if available)
2. Return type if available
3. Purpose based on docstrings, comments, or code logic
4. Usage pattern examples if discernible

Format as a Markdown list with clear headers for each public element.

Code content:
{text}

Inferred Public Interface:"""
)

# Prompt for generating the overall repository summary
OVERALL_SUMMARY_PROMPT = PromptTemplate(
    """Create a concise, high-level summary of this entire software repository based on the provided file summaries and interface descriptions.
Your summary should include:
1. The project's main purpose and functionality
2. Key technologies, frameworks, and languages used
3. Overall architecture and main components
4. Primary external interfaces (APIs, functions, etc.)
5. Notable features or capabilities

Format as Markdown with clear sections. Be informative but concise.

Repository content summaries:
{text}

Repository Summary:"""
)
