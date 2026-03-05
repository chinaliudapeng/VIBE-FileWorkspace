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

    def test_remove_tag_success(self):
        """Test removing a tag from a file."""
        # Add a tag first
        test_file_path = str(self.test_file1.resolve())
        file_entry = FileEntry.get_by_absolute_path(test_file_path)
        Tag.add_tag_to_file(file_entry.id, 'python')

        # Remove the tag
        result = self.runner.invoke(cli, ['remove-tag', '--path', test_file_path, '--tag', 'python'])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('tag', output_data['data'])
        self.assertEqual(output_data['data']['tag'], 'python')
        self.assertIn("Successfully removed tag 'python'", output_data['data']['message'])

        # Verify tag was actually removed
        remaining_tags = Tag.get_tags_for_file(file_entry.id)
        tag_names = [tag.tag_name for tag in remaining_tags]
        self.assertNotIn('python', tag_names)

    def test_remove_tag_file_not_found(self):
        """Test removing a tag from a non-existent file."""
        result = self.runner.invoke(cli, ['remove-tag', '--path', '/nonexistent/path.txt', '--tag', 'test'])

        self.assertEqual(result.exit_code, 1)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertFalse(output_data['success'])
        self.assertIn('error', output_data)
        self.assertIn("File not found", output_data['error'])

    def test_remove_tag_not_found(self):
        """Test removing a non-existent tag from a file."""
        test_file_path = str(self.test_file1.resolve())

        result = self.runner.invoke(cli, ['remove-tag', '--path', test_file_path, '--tag', 'nonexistent'])

        self.assertEqual(result.exit_code, 1)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertFalse(output_data['success'])
        self.assertIn('error', output_data)
        self.assertIn("Tag 'nonexistent' not found on file", output_data['error'])

    def test_list_tags_empty(self):
        """Test listing tags when no tags exist."""
        result = self.runner.invoke(cli, ['list-tags'])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('tags', output_data['data'])
        self.assertIn('total_tags', output_data['data'])
        self.assertEqual(output_data['data']['tags'], [])
        self.assertEqual(output_data['data']['total_tags'], 0)

    def test_list_tags_with_data(self):
        """Test listing tags when tags exist."""
        # Add some tags
        test_file_path = str(self.test_file1.resolve())
        file_entry = FileEntry.get_by_absolute_path(test_file_path)
        Tag.add_tag_to_file(file_entry.id, 'python')
        Tag.add_tag_to_file(file_entry.id, 'test')

        # Add another tag to another file
        test_file_path2 = str(self.test_file2.resolve())
        file_entry2 = FileEntry.get_by_absolute_path(test_file_path2)
        Tag.add_tag_to_file(file_entry2.id, 'documentation')

        result = self.runner.invoke(cli, ['list-tags'])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('tags', output_data['data'])
        self.assertIn('total_tags', output_data['data'])

        # Should have 3 unique tags
        self.assertEqual(output_data['data']['total_tags'], 3)
        self.assertIn('python', output_data['data']['tags'])
        self.assertIn('test', output_data['data']['tags'])
        self.assertIn('documentation', output_data['data']['tags'])

    def test_list_workspaces_empty(self):
        """Test listing workspaces when none exist (after cleanup)."""
        # Clean up the workspace created in setUp
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

        result = self.runner.invoke(cli, ['list-workspaces'])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('workspaces', output_data['data'])
        self.assertIn('total_workspaces', output_data['data'])
        self.assertEqual(output_data['data']['workspaces'], [])
        self.assertEqual(output_data['data']['total_workspaces'], 0)

    def test_list_workspaces_with_data(self):
        """Test listing workspaces when they exist."""
        result = self.runner.invoke(cli, ['list-workspaces'])

        self.assertEqual(result.exit_code, 0)

        # Parse the JSON output
        output_data = json.loads(result.output)

        self.assertTrue(output_data['success'])
        self.assertIn('data', output_data)
        self.assertIn('workspaces', output_data['data'])
        self.assertIn('total_workspaces', output_data['data'])

        # Should have at least the workspace created in setUp
        self.assertGreaterEqual(output_data['data']['total_workspaces'], 1)

        # Check that workspace data contains expected fields
        if output_data['data']['total_workspaces'] > 0:
            workspace = output_data['data']['workspaces'][0]
            self.assertIn('id', workspace)
            self.assertIn('name', workspace)
            self.assertIn('created_at', workspace)

    @patch('core.analytics.WorkspaceAnalytics.get_comprehensive_stats')
    def test_stats_comprehensive(self, mock_get_stats):
        """Test stats command with comprehensive type."""
        mock_get_stats.return_value = {
            "summary": {
                "total_workspaces": 2,
                "total_files": 10,
                "total_unique_tags": 5,
                "database_size_mb": 1.5,
                "tag_coverage": "80.0%"
            },
            "database": {"total_records": 20},
            "workspaces": {"total_workspaces": 2},
            "file_types": {"total_files": 10},
            "tags": {"total_unique_tags": 5}
        }

        result = self.runner.invoke(cli, ['stats'])

        self.assertEqual(result.exit_code, 0)
        response = json.loads(result.output)
        self.assertTrue(response['success'])

        data = response['data']
        self.assertEqual(data['statistics_type'], 'comprehensive')
        self.assertIn('statistics', data)
        self.assertEqual(data['statistics']['summary']['total_workspaces'], 2)

    @patch('core.analytics.WorkspaceAnalytics.get_database_stats')
    def test_stats_database_type(self, mock_get_stats):
        """Test stats command with database type."""
        mock_get_stats.return_value = {
            "database_size_mb": 2.0,
            "total_records": 25,
            "table_counts": {
                "workspace": 2,
                "file_entry": 15,
                "tags": 8
            }
        }

        result = self.runner.invoke(cli, ['stats', '--type', 'database'])

        self.assertEqual(result.exit_code, 0)
        response = json.loads(result.output)
        self.assertTrue(response['success'])

        data = response['data']
        self.assertEqual(data['statistics_type'], 'database')
        self.assertEqual(data['statistics']['database_size_mb'], 2.0)

    @patch('core.analytics.WorkspaceAnalytics.get_workspace_detailed_stats')
    def test_stats_specific_workspace(self, mock_get_stats):
        """Test stats command for specific workspace."""
        # The workspace is created in setUp
        mock_get_stats.return_value = {
            "workspace": {
                "id": self.workspace.id,
                "name": self.workspace.name,
                "created_at": "2024-01-01 10:00:00"
            },
            "file_statistics": {
                "total_files": 5,
                "total_size_mb": 1.2
            }
        }

        result = self.runner.invoke(cli, ['stats', '--workspace', self.workspace.name])

        self.assertEqual(result.exit_code, 0)
        response = json.loads(result.output)
        self.assertTrue(response['success'])

        data = response['data']
        self.assertEqual(data['statistics_type'], f'workspace_{self.workspace.name}')
        self.assertEqual(data['statistics']['workspace']['name'], self.workspace.name)

    def test_stats_workspace_not_found(self):
        """Test stats command with non-existent workspace."""
        result = self.runner.invoke(cli, ['stats', '--workspace', 'NonExistent'])

        self.assertEqual(result.exit_code, 1)
        response = json.loads(result.output)
        self.assertFalse(response['success'])
        self.assertIn("Workspace 'NonExistent' not found", response['error'])

    @patch('core.analytics.WorkspaceAnalytics.get_file_type_stats')
    def test_stats_files_type(self, mock_get_stats):
        """Test stats command with files type."""
        mock_get_stats.return_value = {
            "total_files": 12,
            "unique_file_types": 6,
            "file_type_distribution": [
                {"file_type": "py", "count": 5, "percentage": 41.67},
                {"file_type": "js", "count": 3, "percentage": 25.0},
                {"file_type": "md", "count": 2, "percentage": 16.67}
            ]
        }

        result = self.runner.invoke(cli, ['stats', '--type', 'files'])

        self.assertEqual(result.exit_code, 0)
        response = json.loads(result.output)
        self.assertTrue(response['success'])

        data = response['data']
        self.assertEqual(data['statistics_type'], 'files')
        self.assertEqual(data['statistics']['total_files'], 12)
        self.assertEqual(len(data['statistics']['file_type_distribution']), 3)

    @patch('core.analytics.WorkspaceAnalytics.get_tag_stats')
    def test_stats_tags_type(self, mock_get_stats):
        """Test stats command with tags type."""
        mock_get_stats.return_value = {
            "total_unique_tags": 8,
            "total_tag_instances": 25,
            "files_with_tags": 10,
            "files_without_tags": 2,
            "tag_coverage_percentage": 83.33,
            "most_used_tags": [
                {"tag_name": "python", "usage_count": 8, "percentage": 32.0},
                {"tag_name": "script", "usage_count": 5, "percentage": 20.0}
            ]
        }

        result = self.runner.invoke(cli, ['stats', '--type', 'tags'])

        self.assertEqual(result.exit_code, 0)
        response = json.loads(result.output)
        self.assertTrue(response['success'])

        data = response['data']
        self.assertEqual(data['statistics_type'], 'tags')
        self.assertEqual(data['statistics']['total_unique_tags'], 8)
        self.assertEqual(data['statistics']['tag_coverage_percentage'], 83.33)


if __name__ == '__main__':
    unittest.main()