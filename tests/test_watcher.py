"""
Unit tests for the filesystem watcher module.
"""

import os
import tempfile
import time
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
from watchdog.events import FileCreatedEvent, FileDeletedEvent, FileMovedEvent

from core.watcher import (
    WorkspaceFileHandler,
    FilesystemWatcher,
    get_global_watcher,
    start_watching_workspace,
    stop_watching_workspace,
    start_watching_all_workspaces,
    stop_all_watching
)
from core.models import Workspace, WorkspacePath
from core.scanner import FileEntry
from core.db import initialize_database, get_connection


class TestWorkspaceFileHandler:
    """Test cases for WorkspaceFileHandler."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)

        # Initialize the temporary database
        with patch('core.db.get_db_path', return_value=db_path):
            initialize_database()
            yield db_path

        # Cleanup
        os.unlink(db_path)

    @pytest.fixture
    def sample_workspace(self, temp_db):
        """Create a sample workspace for testing."""
        with patch('core.db.get_db_path', return_value=temp_db):
            workspace = Workspace.create("Test Workspace")
            yield workspace

    @pytest.fixture
    def temp_workspace_dir(self, sample_workspace, temp_db):
        """Create a temporary workspace directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('core.db.get_db_path', return_value=temp_db):
                # Add the temp directory as a workspace path
                WorkspacePath.add_path(
                    sample_workspace.id,
                    temp_dir,
                    'folder'
                )
                yield temp_dir, sample_workspace

    @pytest.fixture
    def handler(self, temp_workspace_dir, temp_db):
        """Create a WorkspaceFileHandler for testing."""
        temp_dir, workspace = temp_workspace_dir
        with patch('core.db.get_db_path', return_value=temp_db):
            mock_watcher = Mock()
            handler = WorkspaceFileHandler(workspace.id, mock_watcher)
            yield handler, temp_dir, workspace

    def test_get_file_type(self, handler, temp_db):
        """Test file type detection."""
        handler_obj, temp_dir, workspace = handler

        # Test various file extensions
        test_cases = [
            ('/path/to/file.py', 'py'),
            ('/path/to/file.txt', 'txt'),
            ('/path/to/file.PDF', 'pdf'),  # Test case insensitive
            ('/path/to/file', 'unknown'),  # No extension
            ('/path/to/.hidden', 'unknown'),  # Hidden file without extension
        ]

        for file_path, expected_type in test_cases:
            result = handler_obj._get_file_type(Path(file_path))
            assert result == expected_type

    def test_calculate_relative_path(self, handler, temp_db):
        """Test relative path calculation."""
        handler_obj, temp_dir, workspace = handler

        with patch('core.db.get_db_path', return_value=temp_db):
            # Test file within workspace folder
            test_file = os.path.join(temp_dir, 'subfolder', 'test.py')
            relative_path = handler_obj._calculate_relative_path(test_file)
            expected = str(Path('subfolder/test.py'))
            assert relative_path == expected

            # Test file outside workspace
            outside_file = '/some/other/path/file.py'
            relative_path = handler_obj._calculate_relative_path(outside_file)
            assert relative_path is None

    def test_on_created_file(self, handler, temp_db):
        """Test file creation event handling."""
        handler_obj, temp_dir, workspace = handler

        with patch('core.db.get_db_path', return_value=temp_db):
            # Create a test file
            test_file = os.path.join(temp_dir, 'test.py')
            Path(test_file).touch()

            # Create file created event
            event = FileCreatedEvent(test_file)

            # Handle the event
            handler_obj.on_created(event)

            # Verify file was added to database
            file_entry = FileEntry.get_by_absolute_path(str(Path(test_file).resolve()))
            assert file_entry is not None
            assert file_entry.workspace_id == workspace.id
            assert file_entry.file_type == 'py'
            assert file_entry.relative_path == 'test.py'

    def test_on_created_directory_ignored(self, handler, temp_db):
        """Test that directory creation events are ignored."""
        handler_obj, temp_dir, workspace = handler

        with patch('core.db.get_db_path', return_value=temp_db):
            # Create directory event
            test_dir = os.path.join(temp_dir, 'newdir')
            event = FileCreatedEvent(test_dir)
            event.is_directory = True

            # Handle the event
            handler_obj.on_created(event)

            # Verify no file entry was created
            file_entry = FileEntry.get_by_absolute_path(str(Path(test_dir).resolve()))
            assert file_entry is None

    def test_on_deleted_file(self, handler, temp_db):
        """Test file deletion event handling."""
        handler_obj, temp_dir, workspace = handler

        with patch('core.db.get_db_path', return_value=temp_db):
            # Create and add a test file to database
            test_file = os.path.join(temp_dir, 'test.py')
            Path(test_file).touch()

            file_entry = FileEntry.create(
                workspace_id=workspace.id,
                relative_path='test.py',
                absolute_path=str(Path(test_file).resolve()),
                file_type='py'
            )

            # Verify file exists in database
            assert FileEntry.get_by_absolute_path(str(Path(test_file).resolve())) is not None

            # Create file deleted event
            event = FileDeletedEvent(test_file)

            # Handle the event
            handler_obj.on_deleted(event)

            # Verify file was removed from database
            file_entry = FileEntry.get_by_absolute_path(str(Path(test_file).resolve()))
            assert file_entry is None

    def test_on_moved_file(self, handler, temp_db):
        """Test file move/rename event handling."""
        handler_obj, temp_dir, workspace = handler

        with patch('core.db.get_db_path', return_value=temp_db):
            # Create original file and add to database
            old_file = os.path.join(temp_dir, 'old.py')
            new_file = os.path.join(temp_dir, 'new.py')
            Path(old_file).touch()

            FileEntry.create(
                workspace_id=workspace.id,
                relative_path='old.py',
                absolute_path=str(Path(old_file).resolve()),
                file_type='py'
            )

            # Create moved event
            event = FileMovedEvent(old_file, new_file)

            # Handle the event
            handler_obj.on_moved(event)

            # Verify old entry was removed and new entry was added
            old_entry = FileEntry.get_by_absolute_path(str(Path(old_file).resolve()))
            new_entry = FileEntry.get_by_absolute_path(str(Path(new_file).resolve()))

            assert old_entry is None
            assert new_entry is not None
            assert new_entry.relative_path == 'new.py'

    def test_on_modified_does_nothing(self, handler, temp_db):
        """Test that file modification events are handled gracefully."""
        handler_obj, temp_dir, workspace = handler

        with patch('core.db.get_db_path', return_value=temp_db):
            # Create a mock modified event
            test_file = os.path.join(temp_dir, 'test.py')
            event = Mock()
            event.src_path = test_file
            event.is_directory = False

            # This should not raise any exceptions
            handler_obj.on_modified(event)


class TestFilesystemWatcher:
    """Test cases for FilesystemWatcher."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)

        # Initialize the temporary database
        with patch('core.db.get_db_path', return_value=db_path):
            initialize_database()
            yield db_path

        # Cleanup
        os.unlink(db_path)

    @pytest.fixture
    def sample_workspace(self, temp_db):
        """Create a sample workspace with paths."""
        with patch('core.db.get_db_path', return_value=temp_db):
            workspace = Workspace.create("Test Workspace")

            # Create temporary directory for workspace
            with tempfile.TemporaryDirectory() as temp_dir:
                WorkspacePath.add_path(
                    workspace.id,
                    temp_dir,
                    'folder'
                )
                yield workspace, temp_dir

    @pytest.fixture
    def watcher(self, temp_db):
        """Create a FilesystemWatcher for testing."""
        with patch('core.db.get_db_path', return_value=temp_db):
            watcher = FilesystemWatcher()
            yield watcher
            # Cleanup
            watcher.stop_all_watching()

    def test_init(self, watcher):
        """Test watcher initialization."""
        assert watcher.watching_workspaces == {}
        assert watcher.workspace_handlers == {}
        assert watcher.is_running is False

    def test_start_watching_workspace_success(self, watcher, sample_workspace, temp_db):
        """Test successfully starting to watch a workspace."""
        workspace, temp_dir = sample_workspace

        with patch('core.db.get_db_path', return_value=temp_db):
            result = watcher.start_watching_workspace(workspace.id)

            assert result is True
            assert workspace.id in watcher.watching_workspaces
            assert workspace.id in watcher.workspace_handlers
            assert watcher.is_running is True

    def test_start_watching_nonexistent_workspace(self, watcher, temp_db):
        """Test starting to watch a non-existent workspace."""
        with patch('core.db.get_db_path', return_value=temp_db):
            result = watcher.start_watching_workspace(999)  # Non-existent ID

            assert result is False
            assert 999 not in watcher.watching_workspaces

    def test_start_watching_workspace_no_paths(self, watcher, temp_db):
        """Test starting to watch a workspace with no paths."""
        with patch('core.db.get_db_path', return_value=temp_db):
            workspace = Workspace.create("Empty Workspace")
            result = watcher.start_watching_workspace(workspace.id)

            assert result is False
            assert workspace.id not in watcher.watching_workspaces

    def test_start_watching_already_watching(self, watcher, sample_workspace, temp_db):
        """Test starting to watch a workspace that's already being watched."""
        workspace, temp_dir = sample_workspace

        with patch('core.db.get_db_path', return_value=temp_db):
            # Start watching first time
            result1 = watcher.start_watching_workspace(workspace.id)
            assert result1 is True

            # Try to start watching again
            result2 = watcher.start_watching_workspace(workspace.id)
            assert result2 is True

    def test_stop_watching_workspace(self, watcher, sample_workspace, temp_db):
        """Test stopping watching a workspace."""
        workspace, temp_dir = sample_workspace

        with patch('core.db.get_db_path', return_value=temp_db):
            # Start watching
            watcher.start_watching_workspace(workspace.id)
            assert workspace.id in watcher.watching_workspaces

            # Stop watching
            result = watcher.stop_watching_workspace(workspace.id)

            assert result is True
            assert workspace.id not in watcher.watching_workspaces
            assert workspace.id not in watcher.workspace_handlers
            assert watcher.is_running is False  # Should stop since no workspaces

    def test_stop_watching_not_watching(self, watcher, temp_db):
        """Test stopping watching a workspace that's not being watched."""
        with patch('core.db.get_db_path', return_value=temp_db):
            result = watcher.stop_watching_workspace(999)
            assert result is False

    def test_start_watching_all_workspaces(self, watcher, temp_db):
        """Test starting to watch all workspaces."""
        with patch('core.db.get_db_path', return_value=temp_db):
            # Create multiple workspaces with paths
            workspace1 = Workspace.create("Workspace 1")
            workspace2 = Workspace.create("Workspace 2")

            with tempfile.TemporaryDirectory() as temp_dir1:
                with tempfile.TemporaryDirectory() as temp_dir2:
                    WorkspacePath.add_path(workspace1.id, temp_dir1, 'folder')
                    WorkspacePath.add_path(workspace2.id, temp_dir2, 'folder')

                    result = watcher.start_watching_all_workspaces()

                    assert result == 2  # Both workspaces should be watched
                    assert workspace1.id in watcher.watching_workspaces
                    assert workspace2.id in watcher.watching_workspaces

    def test_get_watched_workspaces(self, watcher, sample_workspace, temp_db):
        """Test getting currently watched workspaces."""
        workspace, temp_dir = sample_workspace

        with patch('core.db.get_db_path', return_value=temp_db):
            # Initially empty
            watched = watcher.get_watched_workspaces()
            assert watched == {}

            # Start watching
            watcher.start_watching_workspace(workspace.id)

            watched = watcher.get_watched_workspaces()
            assert workspace.id in watched
            assert temp_dir in watched[workspace.id] or str(Path(temp_dir).resolve()) in watched[workspace.id]

    def test_is_watching_workspace(self, watcher, sample_workspace, temp_db):
        """Test checking if a workspace is being watched."""
        workspace, temp_dir = sample_workspace

        with patch('core.db.get_db_path', return_value=temp_db):
            # Initially not watching
            assert watcher.is_watching_workspace(workspace.id) is False

            # Start watching
            watcher.start_watching_workspace(workspace.id)
            assert watcher.is_watching_workspace(workspace.id) is True

            # Stop watching
            watcher.stop_watching_workspace(workspace.id)
            assert watcher.is_watching_workspace(workspace.id) is False

    def test_context_manager(self, temp_db):
        """Test watcher as context manager."""
        with patch('core.db.get_db_path', return_value=temp_db):
            with FilesystemWatcher() as watcher:
                workspace = Workspace.create("Test Workspace")

                with tempfile.TemporaryDirectory() as temp_dir:
                    WorkspacePath.add_path(workspace.id, temp_dir, 'folder')
                    watcher.start_watching_workspace(workspace.id)

                    assert watcher.is_watching_workspace(workspace.id) is True

            # After context exit, should be stopped
            assert watcher.is_running is False


class TestGlobalWatcherFunctions:
    """Test cases for global watcher functions."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)

        # Initialize the temporary database
        with patch('core.db.get_db_path', return_value=db_path):
            initialize_database()
            yield db_path

        # Cleanup
        os.unlink(db_path)

    def test_get_global_watcher(self):
        """Test getting the global watcher instance."""
        watcher1 = get_global_watcher()
        watcher2 = get_global_watcher()

        # Should return the same instance
        assert watcher1 is watcher2

        # Cleanup
        watcher1.stop_all_watching()

    def test_convenience_functions(self, temp_db):
        """Test convenience functions for global watcher."""
        with patch('core.db.get_db_path', return_value=temp_db):
            # Create a workspace with paths
            workspace = Workspace.create("Test Workspace")

            with tempfile.TemporaryDirectory() as temp_dir:
                WorkspacePath.add_path(workspace.id, temp_dir, 'folder')

                # Test start_watching_workspace
                result = start_watching_workspace(workspace.id)
                assert result is True

                # Test stop_watching_workspace
                result = stop_watching_workspace(workspace.id)
                assert result is True

                # Test start_watching_all_workspaces
                count = start_watching_all_workspaces()
                assert count == 1

                # Test stop_all_watching
                stop_all_watching()  # Should not raise any errors


class TestWatcherIntegration:
    """Integration tests for filesystem watcher."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        db_fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(db_fd)

        # Initialize the temporary database
        with patch('core.db.get_db_path', return_value=db_path):
            initialize_database()
            yield db_path

        # Cleanup
        os.unlink(db_path)

    def test_end_to_end_file_operations(self, temp_db):
        """Test end-to-end file operations with real filesystem events."""
        with patch('core.db.get_db_path', return_value=temp_db):
            # Create workspace and watcher
            workspace = Workspace.create("Integration Test Workspace")

            with tempfile.TemporaryDirectory() as temp_dir:
                WorkspacePath.add_path(workspace.id, temp_dir, 'folder')

                with FilesystemWatcher() as watcher:
                    # Start watching
                    watcher.start_watching_workspace(workspace.id)

                    # Give the watcher a moment to start
                    time.sleep(0.1)

                    # Create a file
                    test_file = Path(temp_dir) / 'integration_test.py'
                    test_file.write_text('print("Hello, World!")')

                    # Give the watcher time to detect the file
                    time.sleep(0.2)

                    # Check if file was added to database
                    file_entry = FileEntry.get_by_absolute_path(str(test_file.resolve()))
                    assert file_entry is not None
                    assert file_entry.workspace_id == workspace.id
                    assert file_entry.file_type == 'py'

                    # Delete the file
                    test_file.unlink()

                    # Give the watcher time to detect the deletion
                    time.sleep(0.2)

                    # Check if file was removed from database
                    file_entry = FileEntry.get_by_absolute_path(str(test_file.resolve()))
                    assert file_entry is None

    @pytest.mark.skipif(os.name == 'nt', reason="File operations timing can be unreliable on Windows")
    def test_file_rename_detection(self, temp_db):
        """Test file rename detection with real filesystem events."""
        with patch('core.db.get_db_path', return_value=temp_db):
            # Create workspace
            workspace = Workspace.create("Rename Test Workspace")

            with tempfile.TemporaryDirectory() as temp_dir:
                WorkspacePath.add_path(workspace.id, temp_dir, 'folder')

                with FilesystemWatcher() as watcher:
                    # Start watching
                    watcher.start_watching_workspace(workspace.id)
                    time.sleep(0.1)

                    # Create initial file
                    old_file = Path(temp_dir) / 'old_name.py'
                    old_file.write_text('# Old file')
                    time.sleep(0.2)

                    # Verify file exists in database
                    file_entry = FileEntry.get_by_absolute_path(str(old_file.resolve()))
                    assert file_entry is not None

                    # Rename the file
                    new_file = Path(temp_dir) / 'new_name.py'
                    old_file.rename(new_file)
                    time.sleep(0.3)

                    # Check that old entry is gone and new entry exists
                    old_entry = FileEntry.get_by_absolute_path(str(old_file.resolve()))
                    new_entry = FileEntry.get_by_absolute_path(str(new_file.resolve()))

                    assert old_entry is None
                    assert new_entry is not None
                    assert new_entry.relative_path == 'new_name.py'