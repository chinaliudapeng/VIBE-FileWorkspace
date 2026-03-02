"""
Unit tests for the filesystem scanner functionality.
"""

import unittest
import tempfile
import shutil
import sqlite3
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.db import initialize_database, get_connection, get_db_path
from core.models import Workspace, WorkspacePath, Tag
from core.scanner import FileEntry, FilesystemScanner, scan_workspace, rescan_workspace


class TestFileEntry(unittest.TestCase):
    """Test cases for the FileEntry model."""

    def setUp(self):
        """Set up test database."""
        # Use temporary database file for tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.temp_db_path = self.temp_db.name

        self.original_get_db_path = None
        self.mock_db_path()
        initialize_database()

        # Create a test workspace
        self.workspace = Workspace.create("Test Workspace")

    def mock_db_path(self):
        """Mock the database path to use temporary database."""
        self.original_get_db_path = sys.modules['core.db'].get_db_path

        def mock_get_db_path():
            return self.temp_db_path

        sys.modules['core.db'].get_db_path = mock_get_db_path

    def tearDown(self):
        """Clean up after tests."""
        if self.original_get_db_path:
            sys.modules['core.db'].get_db_path = self.original_get_db_path

        # Clean up temporary database file
        try:
            os.unlink(self.temp_db_path)
        except (OSError, FileNotFoundError):
            pass

    def test_create_file_entry(self):
        """Test creating a file entry."""
        file_entry = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="test/file.txt",
            absolute_path="/absolute/test/file.txt",
            file_type="txt"
        )

        self.assertIsNotNone(file_entry.id)
        self.assertEqual(file_entry.workspace_id, self.workspace.id)
        self.assertEqual(file_entry.relative_path, "test/file.txt")
        self.assertEqual(file_entry.absolute_path, "/absolute/test/file.txt")
        self.assertEqual(file_entry.file_type, "txt")

    def test_create_file_entry_duplicate_absolute_path(self):
        """Test creating file entry with duplicate absolute path fails."""
        FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="test/file.txt",
            absolute_path="/absolute/test/file.txt",
            file_type="txt"
        )

        with self.assertRaises(sqlite3.IntegrityError):
            FileEntry.create(
                workspace_id=self.workspace.id,
                relative_path="different/path.txt",
                absolute_path="/absolute/test/file.txt",  # Same absolute path
                file_type="txt"
            )

    def test_create_file_entry_invalid_workspace(self):
        """Test creating file entry with invalid workspace fails."""
        with self.assertRaises(ValueError) as cm:
            FileEntry.create(
                workspace_id=999,  # Non-existent workspace
                relative_path="test/file.txt",
                absolute_path="/absolute/test/file.txt",
                file_type="txt"
            )

        self.assertIn("Workspace with ID 999 does not exist", str(cm.exception))

    def test_get_files_for_workspace(self):
        """Test retrieving files for a workspace."""
        # Create test files
        file1 = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="a/file1.txt",
            absolute_path="/absolute/a/file1.txt",
            file_type="txt"
        )
        file2 = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="b/file2.py",
            absolute_path="/absolute/b/file2.py",
            file_type="py"
        )

        # Create another workspace with a file
        other_workspace = Workspace.create("Other Workspace")
        FileEntry.create(
            workspace_id=other_workspace.id,
            relative_path="other.txt",
            absolute_path="/absolute/other.txt",
            file_type="txt"
        )

        # Get files for our test workspace
        files = FileEntry.get_files_for_workspace(self.workspace.id)

        self.assertEqual(len(files), 2)
        self.assertEqual(files[0].relative_path, "a/file1.txt")  # Should be sorted by relative_path
        self.assertEqual(files[1].relative_path, "b/file2.py")

    def test_delete_by_absolute_path(self):
        """Test deleting file entry by absolute path."""
        file_entry = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="test/file.txt",
            absolute_path="/absolute/test/file.txt",
            file_type="txt"
        )

        # Delete the file
        result = FileEntry.delete_by_absolute_path("/absolute/test/file.txt")
        self.assertTrue(result)

        # Verify it's gone
        files = FileEntry.get_files_for_workspace(self.workspace.id)
        self.assertEqual(len(files), 0)

        # Try to delete non-existent file
        result = FileEntry.delete_by_absolute_path("/nonexistent/file.txt")
        self.assertFalse(result)

    def test_get_by_absolute_path(self):
        """Test retrieving file entry by absolute path."""
        file_entry = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="test/file.txt",
            absolute_path="/absolute/test/file.txt",
            file_type="txt"
        )

        # Get by absolute path
        retrieved = FileEntry.get_by_absolute_path("/absolute/test/file.txt")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.id, file_entry.id)
        self.assertEqual(retrieved.relative_path, "test/file.txt")

        # Try non-existent path
        retrieved = FileEntry.get_by_absolute_path("/nonexistent/file.txt")
        self.assertIsNone(retrieved)

    def test_search_by_tags_partial_matching(self):
        """Test partial tag search functionality."""
        # Create test files
        file1 = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="project/main.py",
            absolute_path="/absolute/project/main.py",
            file_type="py"
        )
        file2 = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="src/utils.py",
            absolute_path="/absolute/src/utils.py",
            file_type="py"
        )
        file3 = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="docs/readme.md",
            absolute_path="/absolute/docs/readme.md",
            file_type="md"
        )

        # Create another workspace with a file
        other_workspace = Workspace.create("Other Workspace")
        file4 = FileEntry.create(
            workspace_id=other_workspace.id,
            relative_path="other.py",
            absolute_path="/absolute/other.py",
            file_type="py"
        )

        # Add tags to files
        Tag.add_tag_to_file(file1.id, 'python-script')
        Tag.add_tag_to_file(file1.id, 'main-entry')
        Tag.add_tag_to_file(file2.id, 'python-utils')
        Tag.add_tag_to_file(file3.id, 'documentation')
        Tag.add_tag_to_file(file4.id, 'python-other')

        # Test exact matching still works
        files = FileEntry.search_by_tags(['python-script'])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].id, file1.id)

        # Test partial matching - searching for 'python' should match tags containing 'python'
        files = FileEntry.search_by_tags(['python'])
        self.assertEqual(len(files), 3)  # file1, file2, file4 all have tags containing 'python'
        file_ids = [f.id for f in files]
        self.assertIn(file1.id, file_ids)
        self.assertIn(file2.id, file_ids)
        self.assertIn(file4.id, file_ids)

        # Test partial matching with workspace filter
        files = FileEntry.search_by_tags(['python'], workspace_id=self.workspace.id)
        self.assertEqual(len(files), 2)  # Only file1 and file2 from test workspace
        file_ids = [f.id for f in files]
        self.assertIn(file1.id, file_ids)
        self.assertIn(file2.id, file_ids)
        self.assertNotIn(file4.id, file_ids)  # file4 is in other workspace

        # Test partial matching with substring
        files = FileEntry.search_by_tags(['main'])
        self.assertEqual(len(files), 1)  # Only file1 has tag containing 'main'
        self.assertEqual(files[0].id, file1.id)

        # Test multiple partial matches
        files = FileEntry.search_by_tags(['python', 'doc'])
        self.assertEqual(len(files), 4)  # file1, file2, file3 (doc), file4 (python)

        # Test case-insensitive partial matching
        files = FileEntry.search_by_tags(['PYTHON'])
        self.assertEqual(len(files), 3)  # Should still find python-* tags

        # Test non-matching partial search
        files = FileEntry.search_by_tags(['nonexistent'])
        self.assertEqual(len(files), 0)

        # Test empty search
        files = FileEntry.search_by_tags([])
        self.assertEqual(len(files), 0)


class TestFilesystemScanner(unittest.TestCase):
    """Test cases for the FilesystemScanner."""

    def setUp(self):
        """Set up test database and temporary directory structure."""
        # Use temporary database file for tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.temp_db_path = self.temp_db.name

        self.original_get_db_path = None
        self.mock_db_path()
        initialize_database()

        # Create a test workspace
        self.workspace = Workspace.create("Test Workspace")

        # Create temporary directory structure
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create test files and directories
        (self.temp_path / "file1.txt").write_text("Content of file1")
        (self.temp_path / "file2.py").write_text("print('hello')")

        subdir = self.temp_path / "subdir"
        subdir.mkdir()
        (subdir / "nested.json").write_text('{"key": "value"}')
        (subdir / "deep.log").write_text("Log entry")

        deeper = subdir / "deeper"
        deeper.mkdir()
        (deeper / "deep_file.md").write_text("# Markdown")

        # Create a single test file outside the directory
        self.single_file = self.temp_path / "single.txt"
        self.single_file.write_text("Single file content")

    def mock_db_path(self):
        """Mock the database path to use temporary database."""
        self.original_get_db_path = sys.modules['core.db'].get_db_path

        def mock_get_db_path():
            return self.temp_db_path

        sys.modules['core.db'].get_db_path = mock_get_db_path

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)
        if self.original_get_db_path:
            sys.modules['core.db'].get_db_path = self.original_get_db_path

        # Clean up temporary database file
        try:
            os.unlink(self.temp_db_path)
        except (OSError, FileNotFoundError):
            pass

    def test_get_file_type(self):
        """Test file type detection."""
        scanner = FilesystemScanner(self.workspace.id)

        self.assertEqual(scanner._get_file_type(Path("test.txt")), "txt")
        self.assertEqual(scanner._get_file_type(Path("script.py")), "py")
        self.assertEqual(scanner._get_file_type(Path("data.json")), "json")
        self.assertEqual(scanner._get_file_type(Path("README.MD")), "md")  # Case insensitive
        self.assertEqual(scanner._get_file_type(Path("noextension")), "unknown")

    def test_scan_directory(self):
        """Test scanning a directory structure."""
        scanner = FilesystemScanner(self.workspace.id)

        discovered = scanner._scan_directory(self.temp_path, self.temp_path)

        # Should find 7 items total (5 files + 2 directories inside the root)
        # Note: root dir itself is skipped because current_dir == root_path
        self.assertEqual(len(discovered), 8) 

        # Check specific files
        file_paths = {f['relative_path'] for f in discovered}
        expected_files = {
            "subdir",
            str(Path("subdir") / "deeper"),
            "file1.txt",
            "file2.py",
            "single.txt",
            str(Path("subdir") / "nested.json"),
            str(Path("subdir") / "deep.log"),
            str(Path("subdir") / "deeper" / "deep_file.md")
        }
        self.assertEqual(file_paths, expected_files)

        # Check file types
        file_types = {f['relative_path']: f['file_type'] for f in discovered}
        self.assertEqual(file_types["file1.txt"], "txt")
        self.assertEqual(file_types["file2.py"], "py")
        self.assertEqual(file_types[str(Path("subdir") / "nested.json")], "json")

    def test_scan_single_file(self):
        """Test scanning a single file."""
        scanner = FilesystemScanner(self.workspace.id)

        discovered = scanner._scan_single_file(self.single_file, self.temp_path)

        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered[0]['relative_path'], "single.txt")
        self.assertEqual(discovered[0]['file_type'], "txt")
        self.assertTrue(discovered[0]['absolute_path'].endswith("single.txt"))

    def test_scan_workspace_paths_folder(self):
        """Test scanning workspace with folder paths."""
        # Add the temp directory as a workspace path
        WorkspacePath.add_path(self.workspace.id, str(self.temp_path), "folder")

        scanner = FilesystemScanner(self.workspace.id)
        files_added = scanner.scan_workspace_paths()

        # Should have added 8 files (6 files + 2 subdirectories)
        self.assertEqual(files_added, 8)

        # Verify files are in database
        files = FileEntry.get_files_for_workspace(self.workspace.id)
        self.assertEqual(len(files), 8)

        # Check that absolute paths are correctly set
        absolute_paths = {f.absolute_path for f in files}
        expected_path = str(self.temp_path / "file1.txt")
        self.assertIn(expected_path, absolute_paths)

    def test_scan_workspace_paths_single_file(self):
        """Test scanning workspace with single file path."""
        # Add the single file as a workspace path
        WorkspacePath.add_path(self.workspace.id, str(self.single_file), "file")

        scanner = FilesystemScanner(self.workspace.id)
        files_added = scanner.scan_workspace_paths()

        # Should have added 1 file
        self.assertEqual(files_added, 1)

        # Verify file is in database
        files = FileEntry.get_files_for_workspace(self.workspace.id)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].relative_path, "single.txt")
        self.assertEqual(files[0].file_type, "txt")

    def test_scan_workspace_paths_mixed(self):
        """Test scanning workspace with mixed folder and file paths."""
        # Add both folder and single file
        WorkspacePath.add_path(self.workspace.id, str(self.temp_path), "folder")

        # Create another single file outside the directory
        other_file = self.temp_path.parent / "other_single.py"
        other_file.write_text("print('other')")
        WorkspacePath.add_path(self.workspace.id, str(other_file), "file")

        scanner = FilesystemScanner(self.workspace.id)
        files_added = scanner.scan_workspace_paths()

        # Should have added 8 items from folder + 1 single file = 9 items
        self.assertEqual(files_added, 9)

        # Verify files are in database
        files = FileEntry.get_files_for_workspace(self.workspace.id)
        self.assertEqual(len(files), 9)

        # Clean up
        other_file.unlink()

    def test_scan_workspace_paths_nonexistent_path(self):
        """Test scanning with non-existent paths."""
        # Add non-existent path
        WorkspacePath.add_path(self.workspace.id, "/nonexistent/path", "folder")

        scanner = FilesystemScanner(self.workspace.id)
        files_added = scanner.scan_workspace_paths()

        # Should add 0 files
        self.assertEqual(files_added, 0)

    def test_scan_duplicate_files(self):
        """Test that scanning twice doesn't duplicate files."""
        # Add the temp directory as a workspace path
        WorkspacePath.add_path(self.workspace.id, str(self.temp_path), "folder")

        scanner = FilesystemScanner(self.workspace.id)

        # First scan
        files_added1 = scanner.scan_workspace_paths()
        self.assertEqual(files_added1, 8)

        # Second scan should add 0 new files
        files_added2 = scanner.scan_workspace_paths()
        self.assertEqual(files_added2, 0)

        # Still should have 8 items total
        files = FileEntry.get_files_for_workspace(self.workspace.id)
        self.assertEqual(len(files), 8)

    def test_rescan_workspace(self):
        """Test rescanning workspace to detect changes."""
        # Add the temp directory as a workspace path
        WorkspacePath.add_path(self.workspace.id, str(self.temp_path), "folder")

        scanner = FilesystemScanner(self.workspace.id)

        # Initial scan
        files_added = scanner.scan_workspace_paths()
        self.assertEqual(files_added, 8)

        # Add a new file
        new_file = self.temp_path / "new_file.txt"
        new_file.write_text("New content")

        # Remove an existing file
        (self.temp_path / "file1.txt").unlink()

        # Rescan
        stats = scanner.rescan_workspace()

        # Should have removed 1 and added 1
        self.assertEqual(stats['removed'], 1)
        self.assertEqual(stats['added'], 1)
        self.assertEqual(stats['total'], 8)  # Net change is 0

        # Clean up
        new_file.unlink()

    def test_scan_workspace_convenience_function(self):
        """Test the convenience function for scanning."""
        # Add the temp directory as a workspace path
        WorkspacePath.add_path(self.workspace.id, str(self.temp_path), "folder")

        files_added = scan_workspace(self.workspace.id)

        # Should have added 8 items
        self.assertEqual(files_added, 8)

    def test_rescan_workspace_convenience_function(self):
        """Test the convenience function for rescanning."""
        # Add the temp directory as a workspace path
        WorkspacePath.add_path(self.workspace.id, str(self.temp_path), "folder")

        # Initial scan
        scan_workspace(self.workspace.id)

        # Add a new file
        new_file = self.temp_path / "new_file.txt"
        new_file.write_text("New content")

        # Rescan using convenience function
        stats = rescan_workspace(self.workspace.id)

        self.assertIn('added', stats)
        self.assertIn('removed', stats)
        self.assertIn('total', stats)

        # Clean up
        new_file.unlink()


class TestScannerIntegration(unittest.TestCase):
    """Integration tests for scanner with database."""

    def setUp(self):
        """Set up test database."""
        # Use temporary database file for tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.temp_db_path = self.temp_db.name

        self.original_get_db_path = None
        self.mock_db_path()
        initialize_database()

    def mock_db_path(self):
        """Mock the database path to use temporary database."""
        self.original_get_db_path = sys.modules['core.db'].get_db_path

        def mock_get_db_path():
            return self.temp_db_path

        sys.modules['core.db'].get_db_path = mock_get_db_path

    def tearDown(self):
        """Clean up after tests."""
        if self.original_get_db_path:
            sys.modules['core.db'].get_db_path = self.original_get_db_path

        # Clean up temporary database file
        try:
            os.unlink(self.temp_db_path)
        except (OSError, FileNotFoundError):
            pass

    def test_cascade_delete_removes_file_entries(self):
        """Test that deleting workspace removes associated file entries."""
        # Create workspace
        workspace = Workspace.create("Test Workspace")

        # Add file entry
        file_entry = FileEntry.create(
            workspace_id=workspace.id,
            relative_path="test/file.txt",
            absolute_path="/absolute/test/file.txt",
            file_type="txt"
        )

        # Verify file exists
        files = FileEntry.get_files_for_workspace(workspace.id)
        self.assertEqual(len(files), 1)

        # Delete workspace
        Workspace.delete(workspace.id)

        # Verify file entries are gone
        files = FileEntry.get_files_for_workspace(workspace.id)
        self.assertEqual(len(files), 0)

        # Verify direct lookup also fails
        retrieved = FileEntry.get_by_absolute_path("/absolute/test/file.txt")
        self.assertIsNone(retrieved)


class TestFileEntryBatchInsertion(unittest.TestCase):
    """Test cases for batch file insertion functionality."""

    def setUp(self):
        """Set up test database."""
        # Use temporary database file for tests
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.temp_db_path = self.temp_db.name

        # Mock get_db_path to return our test database
        self.db_path_patcher = patch('core.db.get_db_path')
        self.mock_get_db_path = self.db_path_patcher.start()
        self.mock_get_db_path.return_value = self.temp_db_path

        # Initialize test database
        initialize_database()

        # Create a test workspace
        self.workspace = Workspace.create("Test Workspace")

    def tearDown(self):
        """Clean up after tests."""
        self.db_path_patcher.stop()

        # Clean up database file
        try:
            os.unlink(self.temp_db_path)
        except (OSError, FileNotFoundError):
            pass

    def test_create_batch_empty_list(self):
        """Test batch creation with empty list."""
        result = FileEntry.create_batch([])
        self.assertEqual(len(result), 0)

    def test_create_batch_single_file(self):
        """Test batch creation with single file."""
        file_entries = [{
            'workspace_id': self.workspace.id,
            'relative_path': 'test.txt',
            'absolute_path': '/path/to/test.txt',
            'file_type': 'txt'
        }]

        result = FileEntry.create_batch(file_entries)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].relative_path, 'test.txt')
        self.assertEqual(result[0].absolute_path, '/path/to/test.txt')
        self.assertEqual(result[0].file_type, 'txt')
        self.assertEqual(result[0].workspace_id, self.workspace.id)

    def test_create_batch_multiple_files(self):
        """Test batch creation with multiple files."""
        file_entries = []
        for i in range(150):  # Test with 150 files to exceed batch threshold
            file_entries.append({
                'workspace_id': self.workspace.id,
                'relative_path': f'test_{i}.txt',
                'absolute_path': f'/path/to/test_{i}.txt',
                'file_type': 'txt'
            })

        result = FileEntry.create_batch(file_entries)
        self.assertEqual(len(result), 150)

        # Verify all files were inserted
        all_files = FileEntry.get_files_for_workspace(self.workspace.id)
        self.assertEqual(len(all_files), 150)

    def test_create_batch_duplicate_handling(self):
        """Test batch creation handles duplicates correctly."""
        file_entries = [
            {
                'workspace_id': self.workspace.id,
                'relative_path': 'test.txt',
                'absolute_path': '/path/to/test.txt',
                'file_type': 'txt'
            },
            {
                'workspace_id': self.workspace.id,
                'relative_path': 'test.txt',
                'absolute_path': '/path/to/test.txt',  # Duplicate
                'file_type': 'txt'
            }
        ]

        result = FileEntry.create_batch(file_entries)
        self.assertEqual(len(result), 1)  # Only one should be created

    def test_create_batch_nonexistent_workspace(self):
        """Test batch creation with nonexistent workspace."""
        file_entries = [{
            'workspace_id': 99999,  # Non-existent workspace
            'relative_path': 'test.txt',
            'absolute_path': '/path/to/test.txt',
            'file_type': 'txt'
        }]

        with self.assertRaises(ValueError):
            FileEntry.create_batch(file_entries)

    def test_scan_workspace_paths_batch_optimization(self):
        """Test that scan_workspace_paths uses batch insertion for large file sets."""
        # Create a temporary directory with many test files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create 120 test files to exceed batch threshold (100)
            test_files = []
            for i in range(120):
                file_path = Path(temp_dir) / f"test_{i:03d}.txt"
                file_path.write_text(f"Test content {i}")
                test_files.append(file_path)

            # Add temp directory to workspace
            WorkspacePath.add_path(self.workspace.id, temp_dir, 'folder')

            # Create scanner and scan
            scanner = FilesystemScanner(self.workspace.id)

            # Mock the batch creation to verify it's called
            with patch.object(FileEntry, 'create_batch', wraps=FileEntry.create_batch) as mock_batch:
                files_added = scanner.scan_workspace_paths()

                # Verify batch insertion was called
                mock_batch.assert_called_once()

                # Verify correct number of files added
                self.assertEqual(files_added, 120)

                # Verify files are in database
                db_files = FileEntry.get_files_for_workspace(self.workspace.id)
                self.assertEqual(len(db_files), 120)

    def test_scan_workspace_paths_individual_fallback(self):
        """Test that scan_workspace_paths falls back to individual insertion when batch fails."""
        # Create a temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create enough files to trigger batch insertion
            for i in range(105):
                file_path = Path(temp_dir) / f"test_{i:03d}.txt"
                file_path.write_text(f"Test content {i}")

            # Add temp directory to workspace
            WorkspacePath.add_path(self.workspace.id, temp_dir, 'folder')

            # Create scanner
            scanner = FilesystemScanner(self.workspace.id)

            # Mock batch creation to simulate failure
            with patch.object(FileEntry, 'create_batch', side_effect=sqlite3.Error("Simulated batch failure")):
                with patch.object(scanner, '_insert_files_individually', wraps=scanner._insert_files_individually) as mock_individual:
                    files_added = scanner.scan_workspace_paths()

                    # Verify individual insertion was called as fallback
                    mock_individual.assert_called_once()

                    # Files should still be added successfully
                    self.assertEqual(files_added, 105)

    def test_scan_workspace_paths_small_set_uses_individual(self):
        """Test that scan_workspace_paths uses individual insertion for small file sets."""
        # Create a temporary directory with few test files (below batch threshold)
        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(5):  # Only 5 files, below 100 threshold
                file_path = Path(temp_dir) / f"test_{i}.txt"
                file_path.write_text(f"Test content {i}")

            # Add temp directory to workspace
            WorkspacePath.add_path(self.workspace.id, temp_dir, 'folder')

            # Create scanner
            scanner = FilesystemScanner(self.workspace.id)

            # Mock both insertion methods to verify which is called
            with patch.object(FileEntry, 'create_batch') as mock_batch:
                with patch.object(scanner, '_insert_files_individually', wraps=scanner._insert_files_individually) as mock_individual:
                    files_added = scanner.scan_workspace_paths()

                    # Verify batch insertion was NOT called for small set
                    mock_batch.assert_not_called()

                    # Verify individual insertion was called
                    mock_individual.assert_called_once()

                    # Verify correct number of files added
                    self.assertEqual(files_added, 5)


if __name__ == '__main__':
    unittest.main()