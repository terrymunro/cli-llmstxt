"""
Mock testing module for the AI-Powered Repository Analyzer CLI.

This module provides mock functionality for testing without a valid OpenAI API key.
"""

import logging


class MockLLM:
    """
    Mock LLM class for testing without an actual OpenAI API key.
    """

    def __init__(self, model="gpt-4o-mini"):
        """
        Initialize the mock LLM.

        Args:
            model (str): Model name (not used in mock)
        """
        self.model = model
        self.logger = logging.getLogger(__name__)

    def predict(self, prompt, **kwargs):
        """
        Mock prediction function.

        Args:
            prompt (str): Input prompt

        Returns:
            str: Mock response
        """
        self.logger.info(f"Mock LLM received prompt: {prompt[:50]}...")

        # Return mock responses based on prompt content
        if "Markdown documentation" in prompt:
            return "This is a mock summary of Markdown documentation."
        elif "Python code" in prompt:
            return "This is a mock summary of Python code with identified functions and classes."
        elif "JavaScript/TypeScript code" in prompt:
            return "This is a mock summary of JavaScript/TypeScript code."
        elif "Flask code" in prompt:
            return "This is a mock analysis of Flask API endpoints."
        elif "FastAPI code" in prompt:
            return "This is a mock analysis of FastAPI endpoints."
        elif "Repository content summaries" in prompt:
            return "This is a mock high-level summary of the entire repository."
        else:
            return "This is a generic mock response for testing purposes."


def get_mock_response_synthesizer(response_mode=None, llm=None, prompt_template=None):
    """
    Mock function to replace get_response_synthesizer.

    Args:
        response_mode: Not used in mock
        llm: LLM instance (MockLLM) to be used by the synthesizer.
        prompt_template: Prompt template to use.

    Returns:
        MockResponseSynthesizer: Mock response synthesizer
    """
    # llm argument is now present, can be used if MockResponseSynthesizer needs it
    return MockResponseSynthesizer(prompt_template=prompt_template, llm=llm)


class MockResponseSynthesizer:
    """
    Mock response synthesizer for testing.
    """

    def __init__(self, prompt_template, llm=None):
        """
        Initialize the mock response synthesizer.

        Args:
            prompt_template: Prompt template to use
            llm: LLM instance (MockLLM) to use. If None, a new MockLLM is created.
        """
        self.prompt_template = prompt_template
        # self.mock_llm = MockLLM() # OLD
        self.mock_llm = llm if llm else MockLLM() # NEW, use passed llm or create one

    def synthesize(self, query="", nodes=None):
        """
        Mock synthesize function.

        Args:
            query (str): Query string
            nodes (List): List of nodes

        Returns:
            MockResponse: Mock response object
        """
        # Create a mock prompt from the template and nodes
        mock_prompt = self.prompt_template.template
        if nodes and len(nodes) > 0:
            # Add a sample of text from the first node
            mock_prompt += f"\n\nSample text: {nodes[0].text[:100] if hasattr(nodes[0], 'text') else 'Sample text'}"

        # Get mock response
        response_text = self.mock_llm.predict(mock_prompt)

        return MockResponse(response_text)


class MockResponse:
    """
    Mock response object.
    """

    def __init__(self, response_text):
        """
        Initialize the mock response.

        Args:
            response_text (str): Response text
        """
        self.response = response_text
