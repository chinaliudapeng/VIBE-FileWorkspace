"""
Tests for the analytics module.
"""

import os
import tempfile
import unittest
import uuid
from unittest.mock import patch, MagicMock

from core.analytics import WorkspaceAnalytics
from core.models import Workspace, WorkspacePath
from core.scanner import FileEntry
from core.db import initialize_database, get_connection


class TestWorkspaceAnalytics(unittest.TestCase):
    """Test cases for WorkspaceAnalytics functionality."""

    def setUp(self):
        """Set up test database and sample data."""
        # Use in-memory database for tests
        self.test_db_path = ":memory:"

        # Patch get_connection to use test database
        self.connection_patcher = patch('core.analytics.get_connection')
        self.mock_get_connection = self.connection_patcher.start()

        # Create test database connection
        import sqlite3
        self.test_conn = sqlite3.connect(self.test_db_path)
        self.test_conn.row_factory = sqlite3.Row
        self.test_conn.execute("PRAGMA foreign_keys = ON")

        self.mock_get_connection.return_value.__enter__.return_value = self.test_conn
        self.mock_get_connection.return_value.__exit__.return_value = None

        # Initialize database schema manually for test connection
        self._initialize_test_database()

        # Create sample data
        self._create_sample_data()

    def _initialize_test_database(self):
        """Initialize test database schema."""
        cursor = self.test_conn.cursor()

        # Create workspace table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workspace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        ''')

        # Create workspace_path table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workspace_path (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                root_path TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('folder', 'file')),
                hiding_rules TEXT DEFAULT '',
                FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE,
                UNIQUE(workspace_id, root_path)
            )
        ''')

        # Create file_entry table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_entry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                relative_path TEXT NOT NULL,
                absolute_path TEXT NOT NULL UNIQUE,
                file_type TEXT NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE
            )
        ''')

        # Create tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                FOREIGN KEY (file_id) REFERENCES file_entry (id) ON DELETE CASCADE,
                UNIQUE(file_id, tag_name)
            )
        ''')

        self.test_conn.commit()

    def tearDown(self):
        """Clean up test resources."""
        if hasattr(self, 'test_conn'):
            self.test_conn.close()
        self.connection_patcher.stop()

    def _create_sample_data(self):
        """Create sample data for testing."""
        # Create test workspaces
        cursor = self.test_conn.cursor()

        # Insert workspaces
        cursor.execute("""
            INSERT INTO workspace (name, created_at) VALUES
            ('Test Workspace 1', '2024-01-01 10:00:00'),
            ('Test Workspace 2', '2024-01-02 11:00:00')
        """)

        # Insert workspace paths
        cursor.execute("""
            INSERT INTO workspace_path (workspace_id, root_path, type, hiding_rules) VALUES
            (1, '/test/path1', 'folder', '\\.git;\\.vscode'),
            (2, '/test/path2', 'folder', '')
        """)

        # Insert file entries
        cursor.execute("""
            INSERT INTO file_entry (workspace_id, relative_path, absolute_path, file_type) VALUES
            (1, 'file1.py', '/test/path1/file1.py', 'py'),
            (1, 'file2.js', '/test/path1/file2.js', 'js'),
            (1, 'file3.txt', '/test/path1/file3.txt', 'txt'),
            (2, 'readme.md', '/test/path2/readme.md', 'md'),
            (2, 'config.json', '/test/path2/config.json', 'json')
        """)

        # Insert tags
        cursor.execute("""
            INSERT INTO tags (file_id, tag_name) VALUES
            (1, 'python'),
            (1, 'script'),
            (2, 'javascript'),
            (3, 'documentation'),
            (4, 'documentation')
        """)

        self.test_conn.commit()

    @patch('core.analytics.get_db_path')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_get_database_stats(self, mock_getsize, mock_exists, mock_get_db_path):
        """Test database statistics generation."""
        mock_get_db_path.return_value = '/test/db.sqlite'
        mock_exists.return_value = True
        mock_getsize.return_value = 1024 * 1024  # 1MB

        stats = WorkspaceAnalytics.get_database_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('database_size_bytes', stats)
        self.assertIn('database_size_mb', stats)
        self.assertIn('table_counts', stats)
        self.assertIn('total_records', stats)

        # Check table counts
        self.assertEqual(stats['table_counts']['workspace'], 2)
        self.assertEqual(stats['table_counts']['workspace_path'], 2)
        self.assertEqual(stats['table_counts']['file_entry'], 5)
        self.assertEqual(stats['table_counts']['tags'], 5)

        # Check calculations
        self.assertEqual(stats['database_size_bytes'], 1024 * 1024)
        self.assertEqual(stats['database_size_mb'], 1.0)
        self.assertEqual(stats['total_records'], 14)  # 2+2+5+5

    @patch('core.analytics.Workspace.list_all')
    @patch('core.analytics.FileEntry.get_files_for_workspace')
    @patch('core.analytics.WorkspacePath.get_paths_for_workspace')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_get_workspace_stats(self, mock_getsize, mock_exists, mock_get_paths, mock_get_files, mock_list_workspaces):
        """Test workspace statistics generation."""
        # Mock workspace data
        mock_workspace1 = MagicMock()
        mock_workspace1.id = 1
        mock_workspace1.name = "Test Workspace 1"
        mock_workspace1.created_at = "2024-01-01 10:00:00"

        mock_workspace2 = MagicMock()
        mock_workspace2.id = 2
        mock_workspace2.name = "Test Workspace 2"
        mock_workspace2.created_at = "2024-01-02 11:00:00"

        mock_list_workspaces.return_value = [mock_workspace1, mock_workspace2]

        # Mock file data
        mock_file1 = MagicMock()
        mock_file1.absolute_path = "/test/file1.py"
        mock_file2 = MagicMock()
        mock_file2.absolute_path = "/test/file2.js"

        mock_get_files.side_effect = [[mock_file1, mock_file2], []]

        # Mock path data
        mock_path1 = MagicMock()
        mock_path1.root_path = "/test/path1"
        mock_path1.type = "folder"
        mock_path1.hiding_rules = r"\.git"

        mock_get_paths.side_effect = [[mock_path1], []]

        # Mock file system
        mock_exists.return_value = True
        mock_getsize.return_value = 1024

        stats = WorkspaceAnalytics.get_workspace_stats()

        self.assertIsInstance(stats, dict)
        self.assertEqual(stats['total_workspaces'], 2)
        self.assertEqual(stats['total_files_across_all_workspaces'], 2)
        self.assertEqual(stats['average_files_per_workspace'], 1.0)
        self.assertEqual(len(stats['workspaces']), 2)

    def test_get_file_type_stats(self):
        """Test file type statistics generation."""
        stats = WorkspaceAnalytics.get_file_type_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_files', stats)
        self.assertIn('unique_file_types', stats)
        self.assertIn('file_type_distribution', stats)
        self.assertIn('top_file_types', stats)

        # Check values based on sample data
        self.assertEqual(stats['total_files'], 5)
        self.assertGreater(stats['unique_file_types'], 0)

        # Check distribution format
        for file_type_stat in stats['file_type_distribution']:
            self.assertIn('file_type', file_type_stat)
            self.assertIn('count', file_type_stat)
            self.assertIn('percentage', file_type_stat)

    def test_get_tag_stats(self):
        """Test tag statistics generation."""
        stats = WorkspaceAnalytics.get_tag_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_unique_tags', stats)
        self.assertIn('total_tag_instances', stats)
        self.assertIn('files_with_tags', stats)
        self.assertIn('files_without_tags', stats)
        self.assertIn('tag_coverage_percentage', stats)
        self.assertIn('tag_usage_distribution', stats)

        # Check values based on sample data
        self.assertEqual(stats['total_unique_tags'], 4)  # python, script, javascript, documentation
        self.assertEqual(stats['total_tag_instances'], 5)
        self.assertEqual(stats['files_with_tags'], 4)  # 4 different files have tags
        self.assertEqual(stats['files_without_tags'], 1)  # 1 file without tags

        # Check distribution format
        for tag_stat in stats['tag_usage_distribution']:
            self.assertIn('tag_name', tag_stat)
            self.assertIn('usage_count', tag_stat)
            self.assertIn('percentage', tag_stat)

    @patch('core.analytics.WorkspaceAnalytics.get_database_stats')
    @patch('core.analytics.WorkspaceAnalytics.get_workspace_stats')
    @patch('core.analytics.WorkspaceAnalytics.get_file_type_stats')
    @patch('core.analytics.WorkspaceAnalytics.get_tag_stats')
    def test_get_comprehensive_stats(self, mock_tag_stats, mock_file_stats, mock_workspace_stats, mock_db_stats):
        """Test comprehensive statistics generation."""
        # Mock individual stat methods
        mock_db_stats.return_value = {"database_size_mb": 1.0, "total_records": 10}
        mock_workspace_stats.return_value = {"total_workspaces": 2, "total_files_across_all_workspaces": 5}
        mock_file_stats.return_value = {"total_files": 5, "unique_file_types": 4}
        mock_tag_stats.return_value = {"total_unique_tags": 3, "tag_coverage_percentage": 80.0}

        stats = WorkspaceAnalytics.get_comprehensive_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('report_generated_at', stats)
        self.assertIn('database', stats)
        self.assertIn('workspaces', stats)
        self.assertIn('file_types', stats)
        self.assertIn('tags', stats)
        self.assertIn('summary', stats)

        # Check that all individual stat methods were called
        mock_db_stats.assert_called_once()
        mock_workspace_stats.assert_called_once()
        mock_file_stats.assert_called_once()
        mock_tag_stats.assert_called_once()

        # Check summary section
        summary = stats['summary']
        self.assertEqual(summary['total_workspaces'], 2)
        self.assertEqual(summary['total_files'], 5)
        self.assertEqual(summary['total_unique_tags'], 3)
        self.assertEqual(summary['database_size_mb'], 1.0)
        self.assertEqual(summary['tag_coverage'], "80.0%")

    @patch('core.analytics.Workspace.get_by_id')
    @patch('core.analytics.FileEntry.get_files_for_workspace')
    @patch('core.analytics.WorkspacePath.get_paths_for_workspace')
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_get_workspace_detailed_stats(self, mock_getsize, mock_exists, mock_get_paths, mock_get_files, mock_get_workspace):
        """Test detailed workspace statistics generation."""
        # Mock workspace
        mock_workspace = MagicMock()
        mock_workspace.id = 1
        mock_workspace.name = "Test Workspace"
        mock_workspace.created_at = "2024-01-01 10:00:00"
        mock_get_workspace.return_value = mock_workspace

        # Mock files
        mock_file1 = MagicMock()
        mock_file1.relative_path = "src/main.py"
        mock_file1.absolute_path = "/test/src/main.py"
        mock_file1.file_type = "py"

        mock_file2 = MagicMock()
        mock_file2.relative_path = "README.md"
        mock_file2.absolute_path = "/test/README.md"
        mock_file2.file_type = "md"

        mock_get_files.return_value = [mock_file1, mock_file2]

        # Mock paths
        mock_path = MagicMock()
        mock_path.root_path = "/test"
        mock_path.type = "folder"
        mock_path.hiding_rules = r"\.git;\.vscode"
        mock_get_paths.return_value = [mock_path]

        # Mock file system
        mock_exists.return_value = True
        mock_getsize.return_value = 2048

        stats = WorkspaceAnalytics.get_workspace_detailed_stats(1)

        self.assertIsInstance(stats, dict)
        self.assertIn('workspace', stats)
        self.assertIn('file_statistics', stats)
        self.assertIn('directory_structure', stats)
        self.assertIn('path_configuration', stats)
        self.assertIn('tag_statistics', stats)

        # Check workspace info
        self.assertEqual(stats['workspace']['id'], 1)
        self.assertEqual(stats['workspace']['name'], "Test Workspace")

        # Check file statistics
        self.assertEqual(stats['file_statistics']['total_files'], 2)
        self.assertEqual(stats['file_statistics']['total_size_bytes'], 4096)  # 2 files * 2048 bytes each

    def test_get_workspace_detailed_stats_not_found(self):
        """Test detailed workspace stats with non-existent workspace."""
        with patch('core.analytics.Workspace.get_by_id') as mock_get_workspace:
            mock_get_workspace.return_value = None

            with self.assertRaises(ValueError) as context:
                WorkspaceAnalytics.get_workspace_detailed_stats(999)

            self.assertIn("Workspace with ID 999 not found", str(context.exception))


class TestAnalyticsIntegration(unittest.TestCase):
    """Integration tests for analytics functionality."""

    def setUp(self):
        """Set up test database with real connections."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        # Patch database path
        self.db_path_patcher = patch('core.analytics.get_db_path')
        self.mock_get_db_path = self.db_path_patcher.start()
        self.mock_get_db_path.return_value = self.temp_db_path

        # Initialize test database
        with patch('core.models.validate_workspace_path'):  # Disable path validation for integration tests
            initialize_database()

    def tearDown(self):
        """Clean up test resources."""
        self.db_path_patcher.stop()
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_analytics_with_empty_database(self):
        """Test analytics with empty database."""
        stats = WorkspaceAnalytics.get_comprehensive_stats()

        self.assertIsInstance(stats, dict)
        self.assertEqual(stats['workspaces']['total_workspaces'], 0)
        self.assertEqual(stats['file_types']['total_files'], 0)
        self.assertEqual(stats['tags']['total_unique_tags'], 0)

    @patch('core.models.validate_workspace_path')  # Disable path validation
    def test_analytics_with_real_data(self, mock_validate):
        """Test analytics with real workspace data."""
        # Create a real workspace with unique name
        unique_name = f"Test Analytics Workspace {uuid.uuid4().hex[:8]}"
        workspace = Workspace.create(unique_name)
        path = WorkspacePath.add_path(workspace.id, "/tmp/test", "folder")

        # Create some file entries directly in the database
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO file_entry (workspace_id, relative_path, absolute_path, file_type) VALUES
                (?, 'test1.py', '/tmp/test/test1.py', 'py'),
                (?, 'test2.js', '/tmp/test/test2.js', 'js')
            """, (workspace.id, workspace.id))
            conn.commit()

        # Generate analytics
        stats = WorkspaceAnalytics.get_comprehensive_stats()

        # Verify results
        self.assertEqual(stats['workspaces']['total_workspaces'], 1)
        self.assertEqual(stats['file_types']['total_files'], 2)
        self.assertGreater(len(stats['file_types']['file_type_distribution']), 0)


if __name__ == '__main__':
    unittest.main()