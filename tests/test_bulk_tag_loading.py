"""Tests for bulk tag loading functionality to verify N+1 query fix."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

# Import modules under test
from gui.models import FileTableModel
from core.models import Workspace, WorkspacePath, Tag
from core.scanner import FileEntry
from core.db import initialize_database


class TestBulkTagLoading(unittest.TestCase):
    """Test cases for bulk tag loading to prevent N+1 queries."""

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
        self.db_path = Path(self.temp_dir) / 'test_bulk_loading.db'

        # Patch get_db_path to use our test database
        self.db_patcher = patch('core.db.get_db_path')
        self.mock_get_db_path = self.db_patcher.start()
        self.mock_get_db_path.return_value = self.db_path

        # Initialize test database
        initialize_database()

        # Create test data
        self._create_test_data()

    def tearDown(self):
        """Clean up test environment."""
        self.db_patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.temp_dir).rmdir()

    def _create_test_data(self):
        """Create sample data for testing bulk tag loading."""
        # Create workspace
        self.workspace = Workspace.create("Bulk Test Workspace")

        # Add path to workspace
        self.workspace_path = WorkspacePath.add_path(
            workspace_id=self.workspace.id,
            root_path="/test/bulk",
            path_type="folder",
            check_existence=False
        )

        # Create multiple file entries
        self.file_entries = []
        for i in range(5):
            file_entry = FileEntry.create(
                workspace_id=self.workspace.id,
                relative_path=f"file_{i}.py",
                absolute_path=f"/test/bulk/file_{i}.py",
                file_type="python"
            )
            self.file_entries.append(file_entry)

        # Add different tag combinations to files
        # File 0: python, important, test
        Tag.add_tag_to_file(self.file_entries[0].id, "python")
        Tag.add_tag_to_file(self.file_entries[0].id, "important")
        Tag.add_tag_to_file(self.file_entries[0].id, "test")

        # File 1: javascript, web
        Tag.add_tag_to_file(self.file_entries[1].id, "javascript")
        Tag.add_tag_to_file(self.file_entries[1].id, "web")

        # File 2: python, backend
        Tag.add_tag_to_file(self.file_entries[2].id, "python")
        Tag.add_tag_to_file(self.file_entries[2].id, "backend")

        # File 3: no tags

        # File 4: test, debug, urgent
        Tag.add_tag_to_file(self.file_entries[4].id, "test")
        Tag.add_tag_to_file(self.file_entries[4].id, "debug")
        Tag.add_tag_to_file(self.file_entries[4].id, "urgent")

    def test_bulk_tag_loading_functionality(self):
        """Test that Tag.get_tags_for_files_bulk() works correctly."""
        # Get file IDs
        file_ids = [file_entry.id for file_entry in self.file_entries]

        # Call bulk loading method
        tags_by_file = Tag.get_tags_for_files_bulk(file_ids)

        # Verify all file IDs are present in result
        self.assertEqual(set(tags_by_file.keys()), set(file_ids))

        # Verify tag counts
        self.assertEqual(len(tags_by_file[self.file_entries[0].id]), 3)  # python, important, test
        self.assertEqual(len(tags_by_file[self.file_entries[1].id]), 2)  # javascript, web
        self.assertEqual(len(tags_by_file[self.file_entries[2].id]), 2)  # python, backend
        self.assertEqual(len(tags_by_file[self.file_entries[3].id]), 0)  # no tags
        self.assertEqual(len(tags_by_file[self.file_entries[4].id]), 3)  # test, debug, urgent

        # Verify specific tag names (should be sorted alphabetically)
        file_0_tags = [tag.tag_name for tag in tags_by_file[self.file_entries[0].id]]
        self.assertEqual(file_0_tags, ["important", "python", "test"])

        file_1_tags = [tag.tag_name for tag in tags_by_file[self.file_entries[1].id]]
        self.assertEqual(file_1_tags, ["javascript", "web"])

    def test_file_table_model_preload_tags(self):
        """Test that FileTableModel preloads tags correctly."""
        model = FileTableModel()

        # Load workspace files (should trigger tag preloading)
        model.load_workspace_files(self.workspace.id)

        # Verify files are loaded
        self.assertEqual(model.get_file_count(), 5)

        # Verify tags are cached for all files
        for file_entry in self.file_entries:
            cached_tags = model.get_cached_tags(file_entry.id)
            expected_tags = Tag.get_tags_for_file(file_entry.id)

            # Compare tag names (cached tags should match direct query)
            cached_tag_names = [tag.tag_name for tag in cached_tags]
            expected_tag_names = [tag.tag_name for tag in expected_tags]
            self.assertEqual(sorted(cached_tag_names), sorted(expected_tag_names))

    def test_cached_tags_performance_benefit(self):
        """Test that cached tags avoid repeated database queries."""
        model = FileTableModel()

        # Load workspace files to populate cache
        model.load_workspace_files(self.workspace.id)

        # Mock Tag.get_tags_for_file to count database calls
        with patch('core.models.Tag.get_tags_for_file') as mock_get_tags:
            mock_get_tags.return_value = []

            # Access cached tags multiple times
            for _ in range(10):
                for file_entry in self.file_entries:
                    model.get_cached_tags(file_entry.id)

            # get_tags_for_file should not be called when using cached data
            mock_get_tags.assert_not_called()

    def test_empty_file_list_bulk_loading(self):
        """Test bulk loading handles empty file list correctly."""
        result = Tag.get_tags_for_files_bulk([])
        self.assertEqual(result, {})

    def test_nonexistent_file_ids_bulk_loading(self):
        """Test bulk loading handles nonexistent file IDs correctly."""
        nonexistent_ids = [99999, 99998, 99997]
        result = Tag.get_tags_for_files_bulk(nonexistent_ids)

        # Should return empty lists for all requested IDs
        self.assertEqual(set(result.keys()), set(nonexistent_ids))
        for file_id in nonexistent_ids:
            self.assertEqual(result[file_id], [])

    def test_mixed_existing_nonexistent_file_ids(self):
        """Test bulk loading with mix of existing and nonexistent file IDs."""
        existing_id = self.file_entries[0].id
        nonexistent_id = 99999
        mixed_ids = [existing_id, nonexistent_id]

        result = Tag.get_tags_for_files_bulk(mixed_ids)

        # Should handle both correctly
        self.assertEqual(set(result.keys()), set(mixed_ids))
        self.assertGreater(len(result[existing_id]), 0)  # Has tags
        self.assertEqual(result[nonexistent_id], [])  # Empty list

    def test_model_refresh_reloads_tags(self):
        """Test that model refresh reloads tag cache."""
        model = FileTableModel()
        model.load_workspace_files(self.workspace.id)

        # Get initial cached tags
        initial_tags = model.get_cached_tags(self.file_entries[0].id)
        initial_count = len(initial_tags)

        # Add a new tag to the file
        Tag.add_tag_to_file(self.file_entries[0].id, "new_tag")

        # Cached tags should still be old (until refresh)
        self.assertEqual(len(model.get_cached_tags(self.file_entries[0].id)), initial_count)

        # Refresh the model
        model.refresh()

        # Now cached tags should include the new tag
        refreshed_tags = model.get_cached_tags(self.file_entries[0].id)
        self.assertEqual(len(refreshed_tags), initial_count + 1)

        # Verify the new tag is present
        refreshed_tag_names = [tag.tag_name for tag in refreshed_tags]
        self.assertIn("new_tag", refreshed_tag_names)


if __name__ == '__main__':
    unittest.main()