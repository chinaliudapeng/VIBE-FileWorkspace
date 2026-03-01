"""
Tests for CLI interface functionality.

This module tests the CLI commands to ensure they work correctly with
the core database layer.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add the parent directory to the Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cli.main import cli
from core.models import Workspace, WorkspacePath, Tag
from core.scanner import FileEntry
from core.db import initialize_database, get_db_path
from click.testing import CliRunner


class TestCLI(unittest.TestCase):
    """Test cases for CLI functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test database for all tests."""
        # Use a temporary database file for testing
        cls.test_db_path = tempfile.mktemp(suffix='.db')

        # Patch the database path to use our test database
        patcher = patch('core.db.get_db_path')
        mock_get_db_path = patcher.start()
        mock_get_db_path.return_value = cls.test_db_path
        cls.patcher = patcher

        # Initialize the test database
        initialize_database()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        cls.patcher.stop()
        # Remove test database file
        if os.path.exists(cls.test_db_path):
            os.unlink(cls.test_db_path)

    def setUp(self):
        """Set up test data before each test."""
        self.runner = CliRunner()

        # Create unique test workspace name for each test
        import uuid
        workspace_name = f"TestWorkspace_{uuid.uuid4().hex[:8]}"
        self.workspace = Workspace.create(workspace_name)

        # Create temporary test directory and files
        self.test_dir = tempfile.mkdtemp()
        self.test_file1 = Path(self.test_dir) / "test1.py"
        self.test_file2 = Path(self.test_dir) / "test2.txt"

        # Create test files
        self.test_file1.write_text("print('hello')")
        self.test_file2.write_text("test content")

        # Add paths to workspace
        WorkspacePath.add_path(self.workspace.id, str(self.test_dir), "folder")

        # Scan the workspace to populate file entries
        from core.scanner import scan_workspace
        scan_workspace(self.workspace.id)

        # Get file entries for tagging
        self.files = FileEntry.get_files_for_workspace(self.workspace.id)

    def tearDown(self):
        """Clean up after each test."""
        # Remove temporary directory and files
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        # Clear database tables (in reverse order due to foreign keys)
        from core.db import get_connection
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tags")
            cursor.execute("DELETE FROM file_entry")
            cursor.execute("DELETE FROM workspace_path")
            cursor.execute("DELETE FROM workspace")
            conn.commit()
        finally:
            conn.close()

    def test_list_files_success(self):
        """Test the list-files command with a valid workspace."""
        result = self.runner.invoke(cli, ['list-files', '--workspace', self.workspace.name])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('workspace', output_data['data'])
        self.assertIn('files', output_data['data'])
        self.assertEqual(output_data['data']['workspace']['name'], self.workspace.name)
        self.assertEqual(len(output_data['data']['files']), 2)  # test1.py and test2.txt

    def test_list_files_workspace_not_found(self):
        """Test the list-files command with a non-existent workspace."""
        result = self.runner.invoke(cli, ['list-files', '--workspace', 'NonExistent'])

        self.assertEqual(result.exit_code, 1)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertFalse(output_data['success'])
        self.assertIn('error', output_data)
        self.assertIn("Workspace 'NonExistent' not found", output_data['error'])

    def test_add_tag_success(self):
        """Test adding a tag to a file."""
        # Get absolute path of one of our test files
        test_file_path = str(self.test_file1.resolve())

        result = self.runner.invoke(cli, ['add-tag', '--path', test_file_path, '--tag', 'python'])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('tag', output_data['data'])
        self.assertEqual(output_data['data']['tag']['name'], 'python')

    def test_add_tag_file_not_found(self):
        """Test adding a tag to a non-existent file."""
        result = self.runner.invoke(cli, ['add-tag', '--path', '/nonexistent/path.txt', '--tag', 'test'])

        self.assertEqual(result.exit_code, 1)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertFalse(output_data['success'])
        self.assertIn('error', output_data)
        self.assertIn("File not found", output_data['error'])

    def test_get_tags_success(self):
        """Test getting tags for a file."""
        # Add a tag first
        test_file_path = str(self.test_file1.resolve())
        file_entry = FileEntry.get_by_absolute_path(test_file_path)
        Tag.add_tag_to_file(file_entry.id, 'python')
        Tag.add_tag_to_file(file_entry.id, 'test')

        result = self.runner.invoke(cli, ['get-tags', '--path', test_file_path])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('tags', output_data['data'])
        self.assertEqual(len(output_data['data']['tags']), 2)

        # Check tag names
        tag_names = [tag['name'] for tag in output_data['data']['tags']]
        self.assertIn('python', tag_names)
        self.assertIn('test', tag_names)

    def test_search_by_keyword(self):
        """Test searching by keyword."""
        result = self.runner.invoke(cli, ['search', '--keyword', 'test1'])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('results', output_data['data'])
        self.assertGreaterEqual(len(output_data['data']['results']), 1)

    def test_search_by_tags(self):
        """Test searching by tags."""
        # Add tags to files first
        test_file_path = str(self.test_file1.resolve())
        file_entry = FileEntry.get_by_absolute_path(test_file_path)
        Tag.add_tag_to_file(file_entry.id, 'python')

        result = self.runner.invoke(cli, ['search', '--tags', 'python'])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('results', output_data['data'])
        self.assertEqual(len(output_data['data']['results']), 1)

    def test_search_no_criteria(self):
        """Test search command without any criteria should fail."""
        result = self.runner.invoke(cli, ['search'])

        self.assertEqual(result.exit_code, 1)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertFalse(output_data['success'])
        self.assertIn('error', output_data)
        self.assertIn("Must provide either --keyword or --tags", output_data['error'])


if __name__ == '__main__':
    unittest.main()