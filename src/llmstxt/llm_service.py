# src/llmstxt/llm_service.py
"""Service for LLM interactions, handling both real and mock LLMs."""

import os
import logging
from llama_index.llms.openai import OpenAI
from llmstxt.config import OPENAI_API_KEY, DEFAULT_MODEL_NAME
from llmstxt.mock_llm import MockLLM, get_mock_response_synthesizer as get_mock_synth
from llama_index.core.response_synthesizers import (
    get_response_synthesizer,
    ResponseMode,
)

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, use_mock: bool = False, model_name: str = DEFAULT_MODEL_NAME):
        self.use_mock = use_mock
        self.model_name = model_name
        self.llm = self._initialize_llm()

    def _initialize_llm(self):
        if self.use_mock:
            logger.info(f"Using mock LLM (model: {self.model_name})")
            return MockLLM(model=self.model_name)

        if not OPENAI_API_KEY:
            logger.warning(
                "OPENAI_API_KEY not found. Switching to mock LLM. "
                "Set OPENAI_API_KEY environment variable for actual LLM usage."
            )
            self.use_mock = True # Force mock if key is missing
            return MockLLM(model=self.model_name)

        logger.info(f"Initializing OpenAI LLM (model: {self.model_name})")
        # Special handling for GPT-4o models if needed, otherwise standard init
        if self.model_name.startswith("gpt-4o"):
            return OpenAI(model=self.model_name, api_key=OPENAI_API_KEY, strict=False)
        return OpenAI(model=self.model_name, api_key=OPENAI_API_KEY)

    def get_response_synthesizer(self, response_mode: ResponseMode = ResponseMode.TREE_SUMMARIZE, prompt_template=None):
        if self.use_mock:
            # Ensure the mock synthesizer also gets the prompt_template if provided
            return get_mock_synth(
                response_mode=response_mode,
                llm=self.llm, # MockLLM instance
                prompt_template=prompt_template
            )

        # For real LLM
        # Note: LlamaIndex's get_response_synthesizer might not directly use a separate prompt_template argument
        # in the same way for all response_modes. TREE_SUMMARIZE often uses a summary_template.
        # We'll assume the synthesizer handles the template if passed, or it's set on the synthesizer instance.
        synthesizer = get_response_synthesizer(
            response_mode=response_mode,
            llm=self.llm, # This is the actual LLM instance (OpenAI or MockLLM)
            # service_context=self._service_context, # If service_context is used
        )

        # For TREE_SUMMARIZE, the template is often set via summary_template or text_qa_template (for QA-like summarization)
        # Depending on how LlamaIndex's synthesizer uses it, one of these might be appropriate.
        # If prompt_template is a generic QueryBundle or similar, it might not be directly applicable here.
        # Assuming prompt_template is a LlamaIndex PromptTemplate object for text QA / summarization tasks.
        if prompt_template:
            if hasattr(synthesizer, 'summary_template') and response_mode == ResponseMode.TREE_SUMMARIZE:
                 synthesizer.summary_template = prompt_template
            elif hasattr(synthesizer, 'text_qa_template'): # common for query_engine based synthesizers
                 synthesizer.text_qa_template = prompt_template
            # Add other template attributes if necessary for different response modes
            else:
                logger.warning(f"Prompt template provided but not directly set on synthesizer for mode {response_mode}. Synthesizer might use LLM's default.")
        return synthesizer

    @property
    def is_mock(self) -> bool:
        return self.use_mock
