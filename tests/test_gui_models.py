"""Unit tests for GUI models."""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from PySide6.QtCore import Qt

from gui.models import FileTableModel
from core.scanner import FileEntry
from core.models import Workspace
from core.db import initialize_database, get_db_path


class TestFileTableModel(unittest.TestCase):
    """Test cases for FileTableModel."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.temp_db_file = tempfile.mktemp(suffix='.db')

        # Patch the database path to use our temp file
        self.db_patcher = patch('core.db.get_db_path', return_value=self.temp_db_file)
        self.db_patcher.start()

        # Initialize database
        initialize_database()

        # Create model
        self.model = FileTableModel()

        # Create test data
        self.workspace = Workspace.create("Test Workspace")

        # Mock some FileEntry objects for testing
        self.test_files = [
            FileEntry(id=1, workspace_id=self.workspace.id,
                     relative_path="src/main.py", absolute_path="/home/user/test/src/main.py",
                     file_type="python"),
            FileEntry(id=2, workspace_id=self.workspace.id,
                     relative_path="README.md", absolute_path="/home/user/test/README.md",
                     file_type="markdown"),
            FileEntry(id=3, workspace_id=self.workspace.id,
                     relative_path="tests/test_app.py", absolute_path="/home/user/test/tests/test_app.py",
                     file_type="python"),
        ]

    def tearDown(self):
        """Clean up test environment."""
        # Stop the patcher
        self.db_patcher.stop()

        # Remove temp database file
        if os.path.exists(self.temp_db_file):
            os.unlink(self.temp_db_file)

    def test_initial_state(self):
        """Test initial model state."""
        self.assertEqual(self.model.rowCount(), 0)
        self.assertEqual(self.model.columnCount(), 4)
        self.assertIsNone(self.model.get_workspace_id())
        self.assertEqual(self.model.get_file_count(), 0)

    def test_column_count(self):
        """Test column count is correct."""
        self.assertEqual(self.model.columnCount(), 4)

    def test_header_data(self):
        """Test header data."""
        expected_headers = ["Relative Path", "File Type", "Absolute Path", "Tags"]
        for i, expected_header in enumerate(expected_headers):
            header = self.model.headerData(i, Qt.Horizontal, Qt.DisplayRole)
            self.assertEqual(header, expected_header)

    def test_row_count_empty(self):
        """Test row count when model is empty."""
        self.assertEqual(self.model.rowCount(), 0)

    @patch('core.scanner.FileEntry.get_files_for_workspace')
    def test_load_workspace_files(self, mock_get_files):
        """Test loading files for a workspace."""
        mock_get_files.return_value = self.test_files

        self.model.load_workspace_files(self.workspace.id)

        self.assertEqual(self.model.rowCount(), 3)
        self.assertEqual(self.model.get_workspace_id(), self.workspace.id)
        self.assertEqual(self.model.get_file_count(), 3)
        mock_get_files.assert_called_once_with(self.workspace.id)

    @patch('core.scanner.FileEntry.get_files_for_workspace')
    def test_load_workspace_files_error(self, mock_get_files):
        """Test loading files when database error occurs."""
        mock_get_files.side_effect = Exception("Database error")

        with self.assertRaises(Exception):
            self.model.load_workspace_files(self.workspace.id)

        # Model should be reset to empty state
        self.assertEqual(self.model.rowCount(), 0)
        self.assertIsNone(self.model.get_workspace_id())

    def test_clear_files(self):
        """Test clearing files from model."""
        # First load some files
        with patch('core.scanner.FileEntry.get_files_for_workspace', return_value=self.test_files):
            self.model.load_workspace_files(self.workspace.id)
            self.assertEqual(self.model.rowCount(), 3)

        # Now clear
        self.model.clear_files()
        self.assertEqual(self.model.rowCount(), 0)
        self.assertIsNone(self.model.get_workspace_id())
        self.assertEqual(self.model.get_file_count(), 0)

    @patch('core.scanner.FileEntry.get_files_for_workspace')
    def test_data_display_role(self, mock_get_files):
        """Test data method with DisplayRole."""
        mock_get_files.return_value = self.test_files
        self.model.load_workspace_files(self.workspace.id)

        # Test first row data
        index = self.model.index(0, FileTableModel.COL_RELATIVE_PATH)
        self.assertEqual(self.model.data(index, Qt.DisplayRole), "src/main.py")

        index = self.model.index(0, FileTableModel.COL_FILE_TYPE)
        self.assertEqual(self.model.data(index, Qt.DisplayRole), "PYTHON")

        index = self.model.index(0, FileTableModel.COL_ABSOLUTE_PATH)
        self.assertEqual(self.model.data(index, Qt.DisplayRole), "/home/user/test/src/main.py")

        index = self.model.index(0, FileTableModel.COL_TAGS)
        # Tags column returns empty string for DisplayRole (custom delegate handles rendering)
        self.assertEqual(self.model.data(index, Qt.DisplayRole), "")

        # Test second row data
        index = self.model.index(1, FileTableModel.COL_FILE_TYPE)
        self.assertEqual(self.model.data(index, Qt.DisplayRole), "MARKDOWN")

    @patch('core.scanner.FileEntry.get_files_for_workspace')
    def test_data_tooltip_role(self, mock_get_files):
        """Test data method with ToolTipRole."""
        mock_get_files.return_value = self.test_files
        self.model.load_workspace_files(self.workspace.id)

        # Tooltip should show absolute path for all columns
        for col in range(self.model.columnCount()):
            index = self.model.index(0, col)
            tooltip = self.model.data(index, Qt.ToolTipRole)
            self.assertEqual(tooltip, "/home/user/test/src/main.py")

    @patch('core.scanner.FileEntry.get_files_for_workspace')
    def test_data_user_role(self, mock_get_files):
        """Test data method with UserRole."""
        mock_get_files.return_value = self.test_files
        self.model.load_workspace_files(self.workspace.id)

        # UserRole should return the FileEntry object
        index = self.model.index(0, 0)
        file_entry = self.model.data(index, Qt.UserRole)
        self.assertIsInstance(file_entry, FileEntry)
        self.assertEqual(file_entry.relative_path, "src/main.py")

    def test_data_invalid_index(self):
        """Test data method with invalid index."""
        # No data loaded
        index = self.model.index(0, 0)
        self.assertIsNone(self.model.data(index, Qt.DisplayRole))

        # Load data then test out of bounds
        with patch('core.scanner.FileEntry.get_files_for_workspace', return_value=self.test_files):
            self.model.load_workspace_files(self.workspace.id)

        # Test out of bounds row
        index = self.model.index(99, 0)
        self.assertIsNone(self.model.data(index, Qt.DisplayRole))

    @patch('core.scanner.FileEntry.get_files_for_workspace')
    def test_get_file_at_row(self, mock_get_files):
        """Test getting file at specific row."""
        mock_get_files.return_value = self.test_files
        self.model.load_workspace_files(self.workspace.id)

        # Test valid row
        file_entry = self.model.get_file_at_row(0)
        self.assertIsInstance(file_entry, FileEntry)
        self.assertEqual(file_entry.relative_path, "src/main.py")

        # Test invalid row
        self.assertIsNone(self.model.get_file_at_row(-1))
        self.assertIsNone(self.model.get_file_at_row(99))

    @patch('core.scanner.FileEntry.get_files_for_workspace')
    def test_refresh(self, mock_get_files):
        """Test refreshing model data."""
        # Initial load
        mock_get_files.return_value = self.test_files[:2]  # Only 2 files
        self.model.load_workspace_files(self.workspace.id)
        self.assertEqual(self.model.rowCount(), 2)

        # Mock updated data
        mock_get_files.return_value = self.test_files  # All 3 files
        self.model.refresh()

        self.assertEqual(self.model.rowCount(), 3)
        mock_get_files.assert_called_with(self.workspace.id)

    def test_refresh_no_workspace(self):
        """Test refresh when no workspace is loaded."""
        # Should not raise error when no workspace is set
        self.model.refresh()
        self.assertEqual(self.model.rowCount(), 0)

    def test_set_files_directly(self):
        """Test setting files directly for search results."""
        # Create some sample file entries
        files = [
            FileEntry(
                id=10,
                workspace_id=self.workspace.id,
                relative_path="src/main.py",
                absolute_path="/path/to/src/main.py",
                file_type="Python"
            ),
            FileEntry(
                id=11,
                workspace_id=self.workspace.id,
                relative_path="docs/readme.md",
                absolute_path="/path/to/docs/readme.md",
                file_type="Markdown"
            )
        ]

        # Set files directly
        self.model._set_files(files)

        # Verify data
        self.assertEqual(self.model.rowCount(), 2)
        self.assertEqual(self.model.get_file_count(), 2)

        # Verify first file
        index = self.model.index(0, FileTableModel.COL_RELATIVE_PATH)
        self.assertEqual(self.model.data(index, Qt.DisplayRole), "src/main.py")

        # Verify second file
        index = self.model.index(1, FileTableModel.COL_RELATIVE_PATH)
        self.assertEqual(self.model.data(index, Qt.DisplayRole), "docs/readme.md")

        # Verify file objects are accessible
        file_at_row_0 = self.model.get_file_at_row(0)
        self.assertIsNotNone(file_at_row_0)
        self.assertEqual(file_at_row_0.relative_path, "src/main.py")

    def test_set_files_empty_list(self):
        """Test setting empty list of files."""
        # Create and set some files first
        files = [FileEntry(
            id=12,
            workspace_id=self.workspace.id,
            relative_path="test.py",
            absolute_path="/test.py",
            file_type="Python"
        )]
        self.model._set_files(files)
        self.assertEqual(self.model.rowCount(), 1)

        # Now set empty list
        self.model._set_files([])
        self.assertEqual(self.model.rowCount(), 0)
        self.assertEqual(self.model.get_file_count(), 0)


if __name__ == '__main__':
    unittest.main()