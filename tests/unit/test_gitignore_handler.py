import unittest
import tempfile
from pathlib import Path
import os # For os.sep, though pathlib handles slashes well.

# Adjust import path based on project structure
from src.llmstxt.gitignore_handler import GitIgnoreHandler

class TestGitIgnoreHandler(unittest.TestCase):
    def setUp(self):
        self.temp_dir_context = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir_context.name).resolve() # Ensure absolute path

        # Create some files and directories for testing
        # Ensure all paths are created relative to self.temp_dir_path
        (self.temp_dir_path / "file.txt").write_text("content")
        (self.temp_dir_path / "another.log").write_text("log_content")

        (self.temp_dir_path / "build").mkdir()
        (self.temp_dir_path / "build" / "output.o").write_text("binary")
        (self.temp_dir_path / "build" / "deep_build" / "output2.o").mkdir(parents=True, exist_ok=True)
        (self.temp_dir_path / "build" / "deep_build" / "output2.o").write_text("binary2")


        (self.temp_dir_path / "src").mkdir()
        (self.temp_dir_path / "src" / "main.py").write_text("python code")
        (self.temp_dir_path / "src" / "important.log").write_text("important log")
        (self.temp_dir_path / "src" / "subdir").mkdir()
        (self.temp_dir_path / "src" / "subdir" / "sub_main.py").write_text("sub python code")

        (self.temp_dir_path / "docs").mkdir()
        (self.temp_dir_path / "docs" / "README.md").write_text("docs readme")
        (self.temp_dir_path / "docs" / "images").mkdir()
        (self.temp_dir_path / "docs" / "images" / "diagram.png").write_text("png data")

        # For testing outside repo path
        self.outside_dir_context = tempfile.TemporaryDirectory()
        self.outside_dir_path = Path(self.outside_dir_context.name).resolve()
        (self.outside_dir_path / "external_file.txt").write_text("external content")


    def tearDown(self):
        self.temp_dir_context.cleanup()
        self.outside_dir_context.cleanup()

    def _write_gitignore(self, content, subpath_str=""):
        # subpath_str is relative to self.temp_dir_path
        gitignore_file_path = self.temp_dir_path / subpath_str / ".gitignore"
        gitignore_file_path.parent.mkdir(parents=True, exist_ok=True)
        gitignore_file_path.write_text(content)

    def _assert_ignored(self, handler, file_path_str_relative_to_repo, should_be_ignored, msg=None):
        # file_path_str is relative to the repo root (self.temp_dir_path)
        full_path_to_check = self.temp_dir_path / file_path_str_relative_to_repo

        # Ensure file/dir exists for realistic testing if it's supposed to be in the repo
        # For directory patterns ending with '/', we check the dir itself or a file within it.
        is_path_supposed_to_be_dir = file_path_str_relative_to_repo.endswith('/')
        path_to_ensure_exists = full_path_to_check

        if is_path_supposed_to_be_dir:
            path_to_ensure_exists = Path(str(full_path_to_check).rstrip('/')) # Use the actual dir name

        if not path_to_ensure_exists.exists():
            if is_path_supposed_to_be_dir or '.' not in path_to_ensure_exists.name : # crude check for dir
                 path_to_ensure_exists.mkdir(parents=True, exist_ok=True)
            else:
                 path_to_ensure_exists.parent.mkdir(parents=True, exist_ok=True)
                 path_to_ensure_exists.write_text("test content")

        # GitIgnoreHandler's should_ignore expects an absolute path string
        path_str_for_handler = str(full_path_to_check.resolve())

        actual_ignored_status = handler.should_ignore(path_str_for_handler)
        self.assertEqual(
            actual_ignored_status,
            should_be_ignored,
            msg or f"Path '{file_path_str_relative_to_repo}' (resolved: {path_str_for_handler}) "
                   f"ignore status was {actual_ignored_status}, expected {should_be_ignored}. "
                   f"Patterns: {handler.ignore_patterns}"
        )

    def test_empty_gitignore(self):
        self._write_gitignore("# A comment\n\n   \n") # Empty lines and comments
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "file.txt", False)
        self._assert_ignored(handler, "another.log", False)

    def test_basic_filename_pattern(self):
        self._write_gitignore("*.log\ntemp.txt")
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "another.log", True, "another.log by *.log")
        self._assert_ignored(handler, "src/important.log", True, "src/important.log by *.log")
        # Create temp.txt for the test
        (self.temp_dir_path / "temp.txt").write_text("temporary")
        self._assert_ignored(handler, "temp.txt", True, "temp.txt by exact match")
        self._assert_ignored(handler, "file.txt", False)

    def test_directory_pattern_trailing_slash(self):
        self._write_gitignore("build/\ndocs/images/")
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "build/output.o", True, "build/output.o due to build/")
        self._assert_ignored(handler, "docs/images/diagram.png", True, "docs/images/diagram.png due to docs/images/")
        self._assert_ignored(handler, "docs/README.md", False, "docs/README.md not covered by docs/images/")
        self._assert_ignored(handler, "src/main.py", False)

    def test_anchored_pattern_leading_slash(self):
        self._write_gitignore("/another.log\n/docs/README.md")
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "another.log", True, "Root another.log")
        self._assert_ignored(handler, "src/important.log", False, "Nested important.log not matched by anchored /another.log")
        self._assert_ignored(handler, "docs/README.md", True, "Root /docs/README.md")
        self._assert_ignored(handler, "docs/images/diagram.png", False, "Nested diagram.png not matched by anchored /docs/README.md")


    def test_internal_slash_pattern(self):
        self._write_gitignore("src/subdir/sub_main.py")
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "src/subdir/sub_main.py", True)
        self._assert_ignored(handler, "src/main.py", False)

    def test_negation_pattern(self):
        self._write_gitignore("*.log\n!src/important.log\nbuild/")
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "another.log", True, "another.log due to *.log")
        self._assert_ignored(handler, "src/important.log", False, "src/important.log due to negation !src/important.log")
        self._assert_ignored(handler, "build/output.o", True, "build/output.o due to build/")
        # Test order: if negation comes after a more general ignore for the same file.
        self._write_gitignore("src/*\n!src/main.py") # ignore all in src, but not main.py
        handler_order = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler_order, "src/important.log", True, "src/important.log due to src/*")
        self._assert_ignored(handler_order, "src/main.py", False, "src/main.py due to !src/main.py")


    def test_patterns_in_subdir_gitignore(self):
        self._write_gitignore("docs/\n*.o") # Root .gitignore
        self._write_gitignore("*.py\n!main.py", subpath_str="src") # src/.gitignore

        handler = GitIgnoreHandler(str(self.temp_dir_path))

        self._assert_ignored(handler, "docs/README.md", True, "docs/README.md ignored by root: docs/")
        self._assert_ignored(handler, "build/output.o", True, "build/output.o ignored by root: *.o")

        # Testing src/.gitignore effects
        self._assert_ignored(handler, "src/subdir/sub_main.py", True, "src/subdir/sub_main.py ignored by src/*.py")
        self._assert_ignored(handler, "src/main.py", False, "src/main.py not ignored due to src/!main.py")
        self._assert_ignored(handler, "src/important.log", False, "src/important.log not covered by src rules")
        self._assert_ignored(handler, "another.log", False, "another.log not ignored by any rule")


    def test_double_star_pattern(self):
        self._write_gitignore("**/build\nsrc/**/sub_main.py")
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "build/output.o", True, "build/output.o by **/build")

        # Create a nested build dir for testing **/build
        nested_build_path = self.temp_dir_path / "foo" / "build" / "nested.o"
        nested_build_path.parent.mkdir(parents=True, exist_ok=True)
        nested_build_path.write_text("data")
        self._assert_ignored(handler, "foo/build/nested.o", True, "foo/build/nested.o by **/build")

        self._assert_ignored(handler, "src/subdir/sub_main.py", True, "src/subdir/sub_main.py by src/**/sub_main.py")
        self._assert_ignored(handler, "src/main.py", False)

    def test_wildcards_basic(self):
        self._write_gitignore("file?.txt\n*.bin")
        (self.temp_dir_path / "file1.txt").write_text("f1")
        (self.temp_dir_path / "fileA.txt").write_text("fA")
        (self.temp_dir_path / "my.bin").write_text("bin")
        (self.temp_dir_path / "my.txt").write_text("txt")

        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "file1.txt", True, "file1.txt by file?.txt")
        self._assert_ignored(handler, "fileA.txt", True, "fileA.txt by file?.txt")
        self._assert_ignored(handler, "my.bin", True, "my.bin by *.bin")
        self._assert_ignored(handler, "my.txt", False)

    def test_path_outside_repo(self):
        self._write_gitignore("*.txt") # This should not apply to files outside the repo
        handler = GitIgnoreHandler(str(self.temp_dir_path))

        # Use the path from self.outside_dir_path for should_ignore
        external_file_path_str = str(self.outside_dir_path / "external_file.txt")

        # should_ignore should return False for paths outside the repo_path
        # The internal logic of should_ignore checks if path is within repo_path
        self.assertFalse(
            handler.should_ignore(external_file_path_str),
            f"External path {external_file_path_str} should not be processed or ignored by this handler."
        )
        # Sanity check an internal file is still processed
        self._assert_ignored(handler, "file.txt", True, "Internal file.txt should be ignored by *.txt")

    def test_commented_lines_and_empty_lines(self):
        self._write_gitignore("# build/\n   \n*.log\n!important.log # keep this one")
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        self._assert_ignored(handler, "build/output.o", False, "build/output.o should NOT be ignored (commented out)")
        self._assert_ignored(handler, "another.log", True, "another.log should be ignored by *.log")
        # Create important.log for this test
        (self.temp_dir_path / "important.log").write_text("important")
        self._assert_ignored(handler, "important.log", False, "important.log should NOT be ignored (negated)")

    def test_pattern_matching_directory_itself(self):
        # If a pattern "build/" is to ignore the directory "build"
        self._write_gitignore("build/")
        handler = GitIgnoreHandler(str(self.temp_dir_path))
        # Git typically ignores files *within* the directory.
        # Testing a file within 'build' is the most common interpretation.
        self._assert_ignored(handler, "build/output.o", True, "File in ignored directory 'build/'")
        # To check if "build" itself (as a path) is ignored, it depends on how git lists files.
        # Our handler matches paths. If "build" is provided (as a dir path), it should match.
        # The _assert_ignored helper creates a file if path is for a file.
        # For a directory, we might need a specific check or assume files within are representative.
        # Let's check a file within, which is already done.
        # What if the path itself 'build' (the directory) is passed?
        # Our current _matches_pattern has logic for is_dir_pattern.
        # If pattern is "build/", file_path "build", full_file_path points to "build" dir.
        # The `_matches_pattern` logic should correctly identify this.
        self.assertTrue(handler.should_ignore(str(self.temp_dir_path / "build")), "Directory 'build' itself by 'build/'")


if __name__ == '__main__':
    unittest.main()
