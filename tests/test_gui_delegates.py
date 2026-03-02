"""Tests for GUI delegates in the Workspace File Indexer application."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication, QStyleOptionViewItem
from PySide6.QtCore import QModelIndex, Qt, QRect
from PySide6.QtGui import QPainter, QColor

# Import modules under test
from gui.delegates import TagPillDelegate
from core.models import Workspace, WorkspacePath, Tag
from core.scanner import FileEntry
from core.db import initialize_database, get_connection


class TestTagPillDelegate(unittest.TestCase):
    """Test cases for TagPillDelegate."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Create QApplication instance (required for GUI components)
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """Set up test database and sample data."""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / 'test_workspace_indexer.db'

        # Patch get_db_path to use our test database
        self.db_patcher = patch('core.db.get_db_path')
        self.mock_get_db_path = self.db_patcher.start()
        self.mock_get_db_path.return_value = self.db_path

        # Initialize test database
        initialize_database()

        # Create test data
        self._create_test_data()

        # Create delegate instance
        self.delegate = TagPillDelegate()

    def tearDown(self):
        """Clean up test environment."""
        self.db_patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.temp_dir).rmdir()

    def _create_test_data(self):
        """Create sample data for testing."""
        # Create workspace
        self.workspace = Workspace.create("Test Workspace")

        # Add path to workspace
        self.workspace_path = WorkspacePath.add_path(
            workspace_id=self.workspace.id,
            root_path="/test/path",
            path_type="folder"
        )

        # Create file entries
        self.file_entry_with_tags = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="test_file_with_tags.py",
            absolute_path="/test/path/test_file_with_tags.py",
            file_type="python"
        )

        self.file_entry_no_tags = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="test_file_no_tags.py",
            absolute_path="/test/path/test_file_no_tags.py",
            file_type="python"
        )

        # Add tags to first file
        Tag.add_tag_to_file(self.file_entry_with_tags.id, "python")
        Tag.add_tag_to_file(self.file_entry_with_tags.id, "test")
        Tag.add_tag_to_file(self.file_entry_with_tags.id, "important")

    def test_get_tag_color_consistency(self):
        """Test that get_tag_color returns consistent colors for same tag."""
        color1 = self.delegate._get_tag_color("python")
        color2 = self.delegate._get_tag_color("python")
        color3 = self.delegate._get_tag_color("javascript")

        # Same tag should always return same color
        self.assertEqual(color1, color2)

        # Different tags should have different colors (highly likely but not guaranteed)
        # We'll just verify the color is valid
        self.assertIsInstance(color3, QColor)
        self.assertTrue(color3.isValid())

    def test_get_contrasting_text_color_dark_background(self):
        """Test that contrasting text color returns white for dark backgrounds."""
        dark_color = QColor("#1e1e1e")  # Very dark gray
        text_color = self.delegate._get_contrasting_text_color(dark_color)
        self.assertEqual(text_color, QColor("white"))

    def test_get_contrasting_text_color_light_background(self):
        """Test that contrasting text color returns black for light backgrounds."""
        light_color = QColor("#f0f0f0")  # Very light gray
        text_color = self.delegate._get_contrasting_text_color(light_color)
        self.assertEqual(text_color, QColor("black"))

    def test_sizeHint_tags_column(self):
        """Test sizeHint returns appropriate size for tags column."""
        # Create mock index for tags column
        mock_index = Mock()
        mock_index.column.return_value = 3  # COL_TAGS = 3

        # Create mock option
        mock_option = Mock()
        mock_option.rect = QRect(0, 0, 200, 30)

        size_hint = self.delegate.sizeHint(mock_option, mock_index)

        # Should return height of pill + margins
        expected_height = self.delegate.pill_height + (2 * self.delegate.pill_margin)
        self.assertEqual(size_hint.height(), expected_height)
        self.assertEqual(size_hint.width(), 200)

    def test_sizeHint_non_tags_column(self):
        """Test sizeHint defers to parent for non-tags columns."""
        # Create mock index for non-tags column
        mock_index = Mock()
        mock_index.column.return_value = 0  # Not COL_TAGS

        mock_option = Mock()
        mock_option.rect = QRect(0, 0, 200, 30)

        # Mock the parent's sizeHint method
        with patch.object(TagPillDelegate.__bases__[0], 'sizeHint') as mock_parent_sizehint:
            mock_parent_sizehint.return_value = mock_option.rect.size()

            size_hint = self.delegate.sizeHint(mock_option, mock_index)

            # Should call parent's sizeHint
            mock_parent_sizehint.assert_called_once_with(mock_option, mock_index)

    def test_paint_non_tags_column(self):
        """Test paint defers to parent for non-tags columns."""
        # Create mock painter, option, and index
        mock_painter = Mock(spec=QPainter)
        mock_option = Mock(spec=QStyleOptionViewItem)
        mock_index = Mock(spec=QModelIndex)
        mock_index.column.return_value = 0  # Not COL_TAGS

        # Mock the parent's paint method
        with patch.object(TagPillDelegate.__bases__[0], 'paint') as mock_parent_paint:
            self.delegate.paint(mock_painter, mock_option, mock_index)

            # Should call parent's paint method
            mock_parent_paint.assert_called_once_with(mock_painter, mock_option, mock_index)

    def test_paint_tags_column_no_file_entry(self):
        """Test paint handles missing file entry gracefully."""
        # Create mock painter, option, and index
        mock_painter = Mock(spec=QPainter)
        mock_option = Mock(spec=QStyleOptionViewItem)
        mock_index = Mock(spec=QModelIndex)

        mock_index.column.return_value = 3  # COL_TAGS
        mock_index.data.return_value = None  # No file entry

        # Mock the parent's paint method
        with patch.object(TagPillDelegate.__bases__[0], 'paint') as mock_parent_paint:
            self.delegate.paint(mock_painter, mock_option, mock_index)

            # Should call parent's paint method as fallback
            mock_parent_paint.assert_called_once_with(mock_painter, mock_option, mock_index)

    def test_paint_tags_column_with_file_entry_database_error(self):
        """Test paint handles database errors gracefully."""
        # Create mock painter, option, and index
        mock_painter = Mock(spec=QPainter)
        mock_painter.save = Mock()
        mock_painter.restore = Mock()

        mock_option = Mock(spec=QStyleOptionViewItem)
        mock_option.rect = QRect(10, 10, 200, 30)

        mock_index = Mock(spec=QModelIndex)
        mock_index.column.return_value = 3  # COL_TAGS
        mock_index.data.return_value = self.file_entry_with_tags  # Valid file entry

        # Mock the model to raise an exception when getting cached tags
        mock_model = Mock()
        mock_model.get_cached_tags.side_effect = Exception("Database error")
        mock_index.model.return_value = mock_model

        # Mock the parent's paint method
        with patch.object(TagPillDelegate.__bases__[0], 'paint') as mock_parent_paint:
            self.delegate.paint(mock_painter, mock_option, mock_index)

            # Should call parent's paint method as fallback
            mock_parent_paint.assert_called_once_with(mock_painter, mock_option, mock_index)

    def test_paint_tags_column_no_tags(self):
        """Test paint handles file with no tags."""
        # Create mock painter, option, and index
        mock_painter = Mock(spec=QPainter)
        mock_painter.save = Mock()
        mock_painter.restore = Mock()

        mock_option = Mock(spec=QStyleOptionViewItem)
        mock_option.rect = QRect(10, 10, 200, 30)
        mock_option.state = 0  # Not selected
        mock_option.palette = Mock()
        mock_option.palette.base.return_value = QColor("#1e1e1e")

        mock_index = Mock(spec=QModelIndex)
        mock_index.column.return_value = 3  # COL_TAGS
        mock_index.data.return_value = self.file_entry_no_tags  # File with no tags
        mock_index.row.return_value = 0

        # Mock fillRect
        mock_painter.fillRect = Mock()

        self.delegate.paint(mock_painter, mock_option, mock_index)

        # Should save and restore painter
        mock_painter.save.assert_called_once()
        mock_painter.restore.assert_called_once()

        # Should fill background
        mock_painter.fillRect.assert_called()

    def test_color_palette_coverage(self):
        """Test that color palette provides good coverage for different tags."""
        # Test multiple tag names to ensure we get different colors
        colors_seen = set()
        test_tags = ["python", "javascript", "rust", "go", "java", "cpp", "html", "css", "sql", "docker"]

        for tag in test_tags:
            color = self.delegate._get_tag_color(tag)
            colors_seen.add(color.name())

        # We should see multiple different colors
        self.assertGreater(len(colors_seen), 1, "Should generate different colors for different tags")


class TestTagPillDelegateIntegration(unittest.TestCase):
    """Integration tests for TagPillDelegate with actual Qt components."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """Set up test database and sample data."""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()

        # Patch get_connection to use our test database
        self.db_patcher = patch('core.db.get_connection')
        self.mock_get_connection = self.db_patcher.start()

        def create_test_connection():
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.execute('PRAGMA foreign_keys = ON')
            return conn

        self.mock_get_connection.side_effect = create_test_connection

        # Initialize test database
        initialize_database()

        self.delegate = TagPillDelegate()

    def tearDown(self):
        """Clean up test environment."""
        self.db_patcher.stop()
        Path(self.db_path).unlink(missing_ok=True)

    def test_delegate_initialization(self):
        """Test that delegate initializes with correct constants."""
        self.assertIsInstance(self.delegate.pill_height, int)
        self.assertIsInstance(self.delegate.pill_padding, int)
        self.assertIsInstance(self.delegate.pill_margin, int)
        self.assertIsInstance(self.delegate.pill_border_radius, int)
        self.assertIsInstance(self.delegate.font_size, int)
        self.assertIsInstance(self.delegate.color_palette, list)
        self.assertGreater(len(self.delegate.color_palette), 0)

    def test_delegate_color_palette_valid_colors(self):
        """Test that all colors in the palette are valid."""
        for color_string in self.delegate.color_palette:
            color = QColor(color_string)
            self.assertTrue(color.isValid(), f"Color {color_string} should be valid")


if __name__ == '__main__':
    unittest.main()