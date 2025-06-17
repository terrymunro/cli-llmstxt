import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import os
from pathlib import Path
import logging

# Assuming direct import if 'src' is in PYTHONPATH or tests are run as module
from src.llmstxt.processing_engine import ProcessingEngine
from src.llmstxt.llm_service import LLMService # For mocking
from src.llmstxt.prompts import (
    MARKDOWN_SUMMARY_PROMPT,
    PYTHON_CODE_SUMMARY_PROMPT,
    JS_TS_CODE_SUMMARY_PROMPT,
    GENERIC_CODE_SUMMARY_PROMPT,
    OVERALL_SUMMARY_PROMPT
)
from llama_index.core.schema import Document # For creating mock documents
# To mock CodeSplitter's potential ImportError or its constructor
from llama_index.core.node_parser import CodeSplitter, SentenceSplitter, MarkdownNodeParser

# Suppress logging during tests for cleaner output, can be enabled for debugging
logging.disable(logging.CRITICAL)


class TestProcessingEngine(unittest.TestCase):

    def setUp(self):
        self.mock_llm_service = MagicMock(spec=LLMService)
        self.mock_llm_service.is_mock = False

        self.mock_synthesizer = MagicMock()
        self.mock_llm_service.get_response_synthesizer.return_value = self.mock_synthesizer

    # Test __init__
    @patch('src.llmstxt.processing_engine.CodeSplitter', side_effect=ImportError("tree_sitter not found"))
    def test_init_code_splitter_unavailable(self, mock_code_splitter_import_error):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.assertFalse(engine.has_code_splitter, "has_code_splitter should be False if CodeSplitter import fails")

    @patch('src.llmstxt.processing_engine.CodeSplitter') # Assume available
    def test_init_code_splitter_available(self, mock_code_splitter_constructor):
        # Ensure the constructor mock itself doesn't raise an error for multiple calls
        mock_code_splitter_constructor.return_value = MagicMock()
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.assertTrue(engine.has_code_splitter, "has_code_splitter should be True if CodeSplitter is available")
        expected_calls = [
            call(language='python', chunk_lines=40, chunk_lines_overlap=15, max_chars=1500),
            call(language='javascript', chunk_lines=40, chunk_lines_overlap=15, max_chars=1500)
        ]
        mock_code_splitter_constructor.assert_has_calls(expected_calls, any_order=True)

    # --- Test load_documents ---
    @patch('src.llmstxt.processing_engine.SimpleDirectoryReader')
    @patch('src.llmstxt.processing_engine.CustomFileReader') # Target where it's imported
    @patch('src.llmstxt.processing_engine.os.path.getsize')
    @patch('src.llmstxt.processing_engine.Path') # Mock pathlib.Path for repo_dir checks
    def test_load_documents_sdr_success_normal_files(self, MockPath, mock_getsize, MockCustomReader, MockSDR):
        # Setup Path mock
        mock_repo_dir = MagicMock()
        mock_repo_dir.exists.return_value = True
        mock_repo_dir.is_dir.return_value = True
        MockPath.return_value = mock_repo_dir

        mock_doc1 = Document(text="doc1 content", metadata={'file_path': 'file1.py'})
        mock_doc2 = Document(text="doc2 content", metadata={'file_path': 'file2.md'})
        MockSDR.return_value.load_data.return_value = [mock_doc1, mock_doc2]
        mock_getsize.return_value = 10 * 1024 # 10KB

        engine = ProcessingEngine(llm_service=self.mock_llm_service, max_file_size_kb=20)
        documents = engine.load_documents("fake_repo_path", [".py", ".md"], [], None)

        self.assertEqual(len(documents), 2)
        MockSDR.assert_called_once()
        MockCustomReader.assert_not_called()
        self.assertEqual(mock_getsize.call_count, 2)


    @patch('src.llmstxt.processing_engine.SimpleDirectoryReader')
    @patch('src.llmstxt.processing_engine.CustomFileReader')
    @patch('src.llmstxt.processing_engine.os.path.getsize')
    @patch('src.llmstxt.processing_engine.Path')
    def test_load_documents_sdr_success_skip_oversize_empty(self, MockPath, mock_getsize, MockCustomReader, MockSDR):
        mock_repo_dir = MagicMock(); mock_repo_dir.exists.return_value = True; mock_repo_dir.is_dir.return_value = True
        MockPath.return_value = mock_repo_dir

        mock_doc_ok = Document(text="ok content", metadata={'file_path': 'ok.py'})
        mock_doc_large = Document(text="large content", metadata={'file_path': 'large.py'})
        mock_doc_empty = Document(text="", metadata={'file_path': 'empty.py'})

        MockSDR.return_value.load_data.return_value = [mock_doc_ok, mock_doc_large, mock_doc_empty]

        def getsize_side_effect(path):
            if path == 'ok.py': return 10 * 1024 # 10KB
            if path == 'large.py': return 30 * 1024 # 30KB
            if path == 'empty.py': return 1 * 1024 # 1KB (but empty text)
            return 0
        mock_getsize.side_effect = getsize_side_effect

        engine = ProcessingEngine(llm_service=self.mock_llm_service, max_file_size_kb=20)
        documents = engine.load_documents("fake_repo_path", [".py"], [], None)

        self.assertEqual(len(documents), 1)
        self.assertIs(documents[0], mock_doc_ok) # Check it's the correct document object
        MockSDR.assert_called_once()
        MockCustomReader.assert_not_called()

    @patch('src.llmstxt.processing_engine.SimpleDirectoryReader')
    @patch('src.llmstxt.processing_engine.CustomFileReader')
    @patch('src.llmstxt.processing_engine.os.path.getsize')
    @patch('src.llmstxt.processing_engine.Path')
    def test_load_documents_sdr_fails_fallback_to_custom(self, MockPath, mock_getsize, MockCustomReader, MockSDR):
        mock_repo_dir = MagicMock(); mock_repo_dir.exists.return_value = True; mock_repo_dir.is_dir.return_value = True
        MockPath.return_value = mock_repo_dir

        MockSDR.return_value.load_data.side_effect = Exception("SDR Failed!")

        mock_doc_custom = Document(text="custom content", metadata={'file_path': 'custom.py'})
        MockCustomReader.return_value.load_data.return_value = [mock_doc_custom]
        mock_getsize.return_value = 5 * 1024

        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        mock_gitignore_handler = MagicMock()
        documents = engine.load_documents("fake_repo_path", [".py"], ["exclude_pattern"], mock_gitignore_handler)

        self.assertEqual(len(documents), 1)
        self.assertIs(documents[0], mock_doc_custom)
        MockSDR.assert_called_once()
        MockCustomReader.assert_called_once()
        # Check that CustomFileReader was called with correct args
        MockCustomReader.return_value.load_data.assert_called_once_with(
            repo_path="fake_repo_path",
            extensions=[".py"],
            exclusions=["exclude_pattern"],
            max_file_size_kb=engine.max_file_size_kb,
            gitignore_handler=mock_gitignore_handler
        )

    @patch('src.llmstxt.processing_engine.SimpleDirectoryReader')
    @patch('src.llmstxt.processing_engine.CustomFileReader')
    @patch('src.llmstxt.processing_engine.os.path.getsize')
    @patch('src.llmstxt.processing_engine.Path')
    def test_load_documents_sdr_empty_fallback_to_custom(self, MockPath, mock_getsize, MockCustomReader, MockSDR):
        mock_repo_dir = MagicMock()
        mock_repo_dir.exists.return_value = True
        mock_repo_dir.is_dir.return_value = True
        # Simulate that rglob finds files, triggering has_matching_files heuristic
        mock_file_in_repo = MagicMock(spec=Path)
        mock_file_in_repo.is_file.return_value = True
        mock_file_in_repo.match.return_value = True # Matches an extension
        mock_repo_dir.rglob.return_value = iter([mock_file_in_repo])
        MockPath.return_value = mock_repo_dir

        MockSDR.return_value.load_data.return_value = [] # SDR returns empty

        mock_doc_custom = Document(text="custom content", metadata={'file_path': 'custom.py'})
        MockCustomReader.return_value.load_data.return_value = [mock_doc_custom]
        mock_getsize.return_value = 5 * 1024

        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        documents = engine.load_documents("fake_repo_path", [".py"], [], None)

        self.assertEqual(len(documents), 1)
        MockSDR.assert_called_once()
        MockCustomReader.assert_called_once()


    # --- Test parse_document ---
    def test_parse_document_markdown(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        mock_document = Document(text="# Markdown", metadata={'file_path': 'test.md'})
        # Patch the specific parser instance on the engine
        with patch.object(engine.markdown_parser, 'get_nodes_from_documents', return_value=['md_node']) as mock_md_parse_method:
            nodes, file_type = engine.parse_document(mock_document)
            self.assertEqual(nodes, ['md_node'])
            self.assertEqual(file_type, 'markdown')
            mock_md_parse_method.assert_called_once_with([mock_document])

    @patch('src.llmstxt.processing_engine.CodeSplitter') # To make has_code_splitter True
    def test_parse_document_python_codesplitter_available(self, mock_cs_constructor):
        mock_cs_constructor.return_value = MagicMock() # for engine.code_splitter_py
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.assertTrue(engine.has_code_splitter) # Pre-condition

        mock_document = Document(text="def foo(): pass", metadata={'file_path': 'test.py'})
        with patch.object(engine.code_splitter_py, 'get_nodes_from_documents', return_value=['py_node']) as mock_py_parse:
            nodes, file_type = engine.parse_document(mock_document)
            self.assertEqual(nodes, ['py_node'])
            self.assertEqual(file_type, 'python')
            mock_py_parse.assert_called_once_with([mock_document])

    @patch('src.llmstxt.processing_engine.CodeSplitter', side_effect=ImportError) # Make has_code_splitter False
    def test_parse_document_python_codesplitter_unavailable(self, mock_cs_import_error):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.assertFalse(engine.has_code_splitter) # Pre-condition

        mock_document = Document(text="def foo(): pass", metadata={'file_path': 'test.py'})
        with patch.object(engine.sentence_splitter, 'get_nodes_from_documents', return_value=['sentence_node']) as mock_sentence_parse:
            nodes, file_type = engine.parse_document(mock_document)
            self.assertEqual(nodes, ['sentence_node'])
            self.assertEqual(file_type, 'python') # Still identified as python, but parsed by sentence splitter
            mock_sentence_parse.assert_called_once_with([mock_document])

    @patch('src.llmstxt.processing_engine.CodeSplitter') # Available
    def test_parse_document_js_codesplitter_available(self, mock_cs_constructor):
        mock_cs_constructor.return_value = MagicMock()
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.assertTrue(engine.has_code_splitter)

        mock_document = Document(text="function bar() {}", metadata={'file_path': 'test.js'})
        with patch.object(engine.code_splitter_js, 'get_nodes_from_documents', return_value=['js_node']) as mock_js_parse:
            nodes, file_type = engine.parse_document(mock_document)
            self.assertEqual(nodes, ['js_node'])
            self.assertEqual(file_type, 'javascript')
            mock_js_parse.assert_called_once_with([mock_document])

    def test_parse_document_generic_fallback(self): # CodeSplitter available but unknown ext
        engine = ProcessingEngine(llm_service=self.mock_llm_service) # Assumes CodeSplitter available by default mock
        mock_document = Document(text="code content", metadata={'file_path': 'test.java'}) # .java is generic
        with patch.object(engine.sentence_splitter, 'get_nodes_from_documents', return_value=['generic_node']) as mock_sentence_parse:
            nodes, file_type = engine.parse_document(mock_document)
            self.assertEqual(nodes, ['generic_node'])
            self.assertEqual(file_type, 'generic')
            mock_sentence_parse.assert_called_once_with([mock_document])

    def test_parse_document_parser_error_fallback(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        mock_document = Document(text="# Markdown", metadata={'file_path': 'test.md'})
        with patch.object(engine.markdown_parser, 'get_nodes_from_documents', side_effect=Exception("Parse Fail!")), \
             patch.object(engine.sentence_splitter, 'get_nodes_from_documents', return_value=['fallback_node']) as mock_fallback_parse, \
             patch.object(engine.logger, 'error') as mock_logger_error:
            nodes, file_type = engine.parse_document(mock_document)
            self.assertEqual(nodes, ['fallback_node'])
            self.assertEqual(file_type, 'generic') # Falls back to generic type
            mock_fallback_parse.assert_called_once_with([mock_document])
            mock_logger_error.assert_called_once()


    # --- Test summarize_file ---
    def test_summarize_file_python(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.mock_synthesizer.synthesize.return_value = MagicMock(response="python summary")

        mock_nodes = [MagicMock()] # NodeWithScore objects are expected by synthesize
        summary = engine.summarize_file(nodes=mock_nodes, file_type="python", file_path="test.py")

        self.assertIn("### Summary of test.py\n\npython summary\n\n", summary)
        self.mock_llm_service.get_response_synthesizer.assert_called_with(
            response_mode=unittest.mock.ANY,
            prompt_template=PYTHON_CODE_SUMMARY_PROMPT
        )
        self.mock_synthesizer.synthesize.assert_called_once()
        # Ensure nodes passed to synthesize are NodeWithScore
        self.assertTrue(all(isinstance(n, MagicMock) or hasattr(n, 'score') for n in self.mock_synthesizer.synthesize.call_args[1]['nodes']))


    def test_summarize_file_markdown(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.mock_synthesizer.synthesize.return_value = MagicMock(response="md summary")
        summary = engine.summarize_file(nodes=[MagicMock()], file_type="markdown", file_path="README.md")
        self.assertIn("### Summary of README.md\n\nmd summary\n\n", summary)
        self.mock_llm_service.get_response_synthesizer.assert_called_with(
            response_mode=unittest.mock.ANY, prompt_template=MARKDOWN_SUMMARY_PROMPT)

    def test_summarize_file_js(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.mock_synthesizer.synthesize.return_value = MagicMock(response="js summary")
        summary = engine.summarize_file(nodes=[MagicMock()], file_type="javascript", file_path="script.js")
        self.assertIn("### Summary of script.js\n\njs summary\n\n", summary)
        self.mock_llm_service.get_response_synthesizer.assert_called_with(
            response_mode=unittest.mock.ANY, prompt_template=JS_TS_CODE_SUMMARY_PROMPT)

    def test_summarize_file_generic(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.mock_synthesizer.synthesize.return_value = MagicMock(response="generic summary")
        summary = engine.summarize_file(nodes=[MagicMock()], file_type="generic", file_path="data.xml")
        self.assertIn("### Summary of data.xml\n\ngeneric summary\n\n", summary)
        self.mock_llm_service.get_response_synthesizer.assert_called_with(
            response_mode=unittest.mock.ANY, prompt_template=GENERIC_CODE_SUMMARY_PROMPT)

    def test_summarize_file_synthesize_error(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.mock_synthesizer.synthesize.side_effect = Exception("LLM Error!")
        with patch.object(engine.logger, 'error') as mock_logger_error:
            summary = engine.summarize_file(nodes=[MagicMock()], file_type="python", file_path="error.py")
            self.assertIn("### Summary of error.py\n\n*Error generating summary: LLM Error!*\n\n", summary)
            mock_logger_error.assert_called_once()


    # --- Test summarize_repository ---
    def test_summarize_repository_normal_content(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.mock_synthesizer.synthesize.return_value = MagicMock(response="repo summary")

        content = "a" * 1000
        summary = engine.summarize_repository(content, max_chars=2000)

        self.assertIn("# Repository Summary\n\nrepo summary\n", summary)
        self.mock_llm_service.get_response_synthesizer.assert_called_with(
            response_mode=unittest.mock.ANY, prompt_template=OVERALL_SUMMARY_PROMPT)

        # Check text passed to sentence_splitter
        with patch.object(engine.sentence_splitter, 'get_nodes_from_documents', return_value=['node']) as mock_split:
            engine.summarize_repository(content, max_chars=2000)
            called_doc_text = mock_split.call_args[0][0][0].text
            self.assertEqual(len(called_doc_text), 1000)


    def test_summarize_repository_truncation(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.mock_synthesizer.synthesize.return_value = MagicMock(response="repo summary")

        long_content = "a" * 2000
        # Patch logger to check for truncation warning (optional, good for thoroughness)
        with patch.object(engine.logger, 'info') as mock_logger_info, \
             patch.object(engine.sentence_splitter, 'get_nodes_from_documents', return_value=['node']) as mock_split:
            summary = engine.summarize_repository(long_content, max_chars=1000)

            self.assertIn("# Repository Summary\n\nrepo summary\n", summary)
            # Check that truncation log message occurred
            self.assertTrue(any("Truncating content" in str(c) for c in mock_logger_info.call_args_list))
            # Check that the content passed to sentence_splitter was indeed truncated
            called_doc_text = mock_split.call_args[0][0][0].text
            self.assertEqual(len(called_doc_text), 1000)


    def test_summarize_repository_synthesize_error(self):
        engine = ProcessingEngine(llm_service=self.mock_llm_service)
        self.mock_synthesizer.synthesize.side_effect = Exception("Overall LLM Error!")
        with patch.object(engine.logger, 'error') as mock_logger_error:
            summary = engine.summarize_repository("some content", max_chars=1000)
            self.assertIn("# Repository Summary\n\n*Error generating summary*\n", summary) # Check specific error message
            mock_logger_error.assert_called_once()

if __name__ == '__main__':
    # Re-enable logging if running tests directly for debugging
    # logging.disable(logging.NOTSET)
    unittest.main()
