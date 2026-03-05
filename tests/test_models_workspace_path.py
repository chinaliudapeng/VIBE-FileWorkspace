"""
Unit tests for WorkspacePath model CRUD operations.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from core.models import Workspace, WorkspacePath
from core.db import initialize_database, get_db_path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temporary directory for the test database
    temp_dir = tempfile.mkdtemp()
    temp_db_path = Path(temp_dir) / 'test_workspace_indexer.db'

    # Mock the get_db_path function to use our temporary database
    with patch('core.db.get_db_path') as mock_get_db_path:
        mock_get_db_path.return_value = temp_db_path

        # Initialize the test database
        initialize_database()

        yield temp_db_path

        # Clean up
        if temp_db_path.exists():
            os.unlink(temp_db_path)
        os.rmdir(temp_dir)


@pytest.fixture
def sample_workspace(temp_db):
    """Create a sample workspace for testing."""
    return Workspace.create("Test Workspace")


class TestWorkspacePathModel:
    """Test cases for WorkspacePath model."""

    def test_add_path_folder_success(self, sample_workspace):
        """Test successfully adding a folder path to workspace."""
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/folder",
            "folder",
            check_existence=False
        )

        assert workspace_path.id is not None
        assert workspace_path.workspace_id == sample_workspace.id
        assert workspace_path.root_path == "/path/to/folder"
        assert workspace_path.path_type == "folder"

    def test_add_path_file_success(self, sample_workspace):
        """Test successfully adding a file path to workspace."""
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/file.txt",
            "file",
            check_existence=False
        )

        assert workspace_path.id is not None
        assert workspace_path.workspace_id == sample_workspace.id
        assert workspace_path.root_path == "/path/to/file.txt"
        assert workspace_path.path_type == "file"

    def test_add_path_invalid_type_fails(self, sample_workspace):
        """Test that adding path with invalid type fails."""
        with pytest.raises(ValueError, match="path_type must be 'folder' or 'file'"):
            WorkspacePath.add_path(
                sample_workspace.id,
                "/path/to/something",
                "invalid",
                check_existence=False
            )

    def test_add_path_empty_path_fails(self, sample_workspace):
        """Test that adding empty path fails."""
        with pytest.raises(ValueError, match="Path cannot be empty"):
            WorkspacePath.add_path(
                sample_workspace.id,
                "",
                "folder",
                check_existence=False
            )

    def test_add_path_whitespace_path_fails(self, sample_workspace):
        """Test that adding whitespace-only path fails."""
        with pytest.raises(ValueError, match="Path cannot be empty"):
            WorkspacePath.add_path(
                sample_workspace.id,
                "   \t\n   ",
                "folder",
                check_existence=False
            )

    def test_add_path_nonexistent_workspace_fails(self, temp_db):
        """Test that adding path to non-existent workspace fails."""
        with pytest.raises(ValueError, match="Workspace with ID 99999 does not exist"):
            WorkspacePath.add_path(
                99999,
                "/path/to/folder",
                "folder",
                check_existence=False
            )

    def test_add_path_duplicate_fails(self, sample_workspace):
        """Test that adding duplicate path fails."""
        WorkspacePath.add_path(
            sample_workspace.id,
            "/duplicate/path",
            "folder",
            check_existence=False
        )

        with pytest.raises(sqlite3.IntegrityError):
            WorkspacePath.add_path(
                sample_workspace.id,
                "/duplicate/path",
                "file",  # Same path, different type should still fail
                check_existence=False
            )

    def test_add_path_whitespace_trimming(self, sample_workspace):
        """Test that leading whitespace is trimmed from paths."""
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "  /path/with/normal_name",
            "folder",
            check_existence=False
        )

        assert workspace_path.root_path == "/path/with/normal_name"

    def test_remove_path_success(self, sample_workspace):
        """Test successfully removing a path from workspace."""
        # Add a path first
        WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/remove",
            "folder",
            check_existence=False
        )

        # Remove it
        result = WorkspacePath.remove_path(sample_workspace.id, "/path/to/remove")
        assert result is True

        # Verify it's gone
        paths = WorkspacePath.get_paths_for_workspace(sample_workspace.id)
        assert len(paths) == 0

    def test_remove_path_not_found(self, sample_workspace):
        """Test removing non-existent path returns False."""
        result = WorkspacePath.remove_path(sample_workspace.id, "/non/existent/path")
        assert result is False

    def test_remove_path_whitespace_trimming(self, sample_workspace):
        """Test that whitespace is trimmed when removing paths."""
        # Add a path
        WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/remove",
            "folder",
            check_existence=False
        )

        # Remove with extra whitespace
        result = WorkspacePath.remove_path(sample_workspace.id, "  /path/to/remove  ")
        assert result is True

    def test_remove_by_id_success(self, sample_workspace):
        """Test successfully removing a path by ID."""
        # Add a path first
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/remove",
            "folder",
            check_existence=False
        )

        # Remove it by ID
        result = WorkspacePath.remove_by_id(workspace_path.id)
        assert result is True

        # Verify it's gone
        paths = WorkspacePath.get_paths_for_workspace(sample_workspace.id)
        assert len(paths) == 0

    def test_remove_by_id_not_found(self, temp_db):
        """Test removing path by non-existent ID returns False."""
        result = WorkspacePath.remove_by_id(99999)
        assert result is False

    def test_get_paths_for_workspace_empty(self, sample_workspace):
        """Test getting paths when workspace has no paths."""
        paths = WorkspacePath.get_paths_for_workspace(sample_workspace.id)
        assert paths == []

    def test_get_paths_for_workspace_with_data(self, sample_workspace):
        """Test getting paths when workspace has multiple paths."""
        # Add test paths
        path1 = WorkspacePath.add_path(sample_workspace.id, "/alpha/folder", "folder", check_existence=False)
        path2 = WorkspacePath.add_path(sample_workspace.id, "/beta/file.txt", "file", check_existence=False)
        path3 = WorkspacePath.add_path(sample_workspace.id, "/gamma/folder", "folder", check_existence=False)

        paths = WorkspacePath.get_paths_for_workspace(sample_workspace.id)

        # Should be ordered by type ASC, path ASC (files before folders)
        assert len(paths) == 3
        assert paths[0].root_path == "/beta/file.txt"
        assert paths[0].path_type == "file"
        assert paths[1].root_path == "/alpha/folder"
        assert paths[1].path_type == "folder"
        assert paths[2].root_path == "/gamma/folder"
        assert paths[2].path_type == "folder"

        # Verify all properties are set
        for path in paths:
            assert path.id is not None
            assert path.workspace_id == sample_workspace.id
            assert path.root_path != ""
            assert path.path_type in ("file", "folder")

    def test_get_by_id_success(self, sample_workspace):
        """Test successfully retrieving workspace path by ID."""
        created_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/test/path",
            "folder",
            check_existence=False
        )

        retrieved_path = WorkspacePath.get_by_id(created_path.id)

        assert retrieved_path is not None
        assert retrieved_path.id == created_path.id
        assert retrieved_path.workspace_id == sample_workspace.id
        assert retrieved_path.root_path == "/test/path"
        assert retrieved_path.path_type == "folder"

    def test_get_by_id_not_found(self, temp_db):
        """Test retrieving workspace path by non-existent ID."""
        path = WorkspacePath.get_by_id(99999)
        assert path is None

    def test_path_exists_true(self, sample_workspace):
        """Test path_exists returns True for existing path."""
        WorkspacePath.add_path(
            sample_workspace.id,
            "/existing/path",
            "folder",
            check_existence=False
        )

        exists = WorkspacePath.path_exists(sample_workspace.id, "/existing/path")
        assert exists is True

    def test_path_exists_false(self, sample_workspace):
        """Test path_exists returns False for non-existent path."""
        exists = WorkspacePath.path_exists(sample_workspace.id, "/non/existent/path")
        assert exists is False

    def test_path_exists_whitespace_trimming(self, sample_workspace):
        """Test that path_exists trims whitespace."""
        WorkspacePath.add_path(
            sample_workspace.id,
            "/test/path",
            "folder",
            check_existence=False
        )

        exists = WorkspacePath.path_exists(sample_workspace.id, "  /test/path  ")
        assert exists is True

    def test_workspace_path_to_dict(self, sample_workspace):
        """Test converting workspace path to dictionary."""
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/dict/test",
            "folder",
            check_existence=False
        )

        path_dict = workspace_path.to_dict()

        assert isinstance(path_dict, dict)
        assert path_dict['id'] == workspace_path.id
        assert path_dict['workspace_id'] == sample_workspace.id
        assert path_dict['root_path'] == "/dict/test"
        assert path_dict['type'] == "folder"

    def test_workspace_path_str_representation(self, sample_workspace):
        """Test string representation of workspace path."""
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/string/test",
            "file",
            check_existence=False
        )

        str_repr = str(workspace_path)

        assert "WorkspacePath(" in str_repr
        assert "/string/test" in str_repr
        assert "file" in str_repr
        assert str(workspace_path.id) in str_repr
        assert str(sample_workspace.id) in str_repr

    def test_workspace_path_constructor(self, temp_db):
        """Test workspace path constructor with different parameters."""
        # Test with all parameters
        path1 = WorkspacePath(id=1, workspace_id=2, root_path="/test", path_type="file")
        assert path1.id == 1
        assert path1.workspace_id == 2
        assert path1.root_path == "/test"
        assert path1.path_type == "file"

        # Test with defaults
        path2 = WorkspacePath()
        assert path2.id is None
        assert path2.workspace_id == 0
        assert path2.root_path == ""
        assert path2.path_type == "folder"

    def test_cascade_delete_workspace_removes_paths(self, temp_db):
        """Test that deleting workspace removes associated paths via CASCADE DELETE."""
        # Create workspace and add paths
        workspace = Workspace.create("Cascade Test")
        path1 = WorkspacePath.add_path(workspace.id, "/path1", "folder", check_existence=False)
        path2 = WorkspacePath.add_path(workspace.id, "/path2", "file", check_existence=False)

        # Verify paths exist
        paths = WorkspacePath.get_paths_for_workspace(workspace.id)
        assert len(paths) == 2

        # Delete workspace
        Workspace.delete(workspace.id)

        # Verify paths are gone
        paths = WorkspacePath.get_paths_for_workspace(workspace.id)
        assert len(paths) == 0

        # Verify paths cannot be retrieved by ID
        assert WorkspacePath.get_by_id(path1.id) is None
        assert WorkspacePath.get_by_id(path2.id) is None

    def test_add_path_with_hiding_rules(self, sample_workspace):
        """Test adding a workspace path with hiding rules."""
        hiding_rules = r".*\.tmp;.*\.log;node_modules"
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/folder",
            "folder",
            hiding_rules,
            check_existence=False
        )

        assert workspace_path.id is not None
        assert workspace_path.workspace_id == sample_workspace.id
        assert workspace_path.root_path == "/path/to/folder"
        assert workspace_path.path_type == "folder"
        assert workspace_path.hiding_rules == hiding_rules

    def test_add_path_without_hiding_rules(self, sample_workspace):
        """Test adding a workspace path without hiding rules (default empty)."""
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/folder",
            "folder",
            check_existence=False
        )

        assert workspace_path.hiding_rules == ""

    def test_update_hiding_rules(self, sample_workspace):
        """Test updating hiding rules for an existing workspace path."""
        # Create path without hiding rules
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/folder",
            "folder",
            check_existence=False
        )

        # Update hiding rules
        new_rules = r".*\.cache;.*\.bak;dist/"
        success = WorkspacePath.update_hiding_rules(workspace_path.id, new_rules)
        assert success

        # Verify update
        updated_path = WorkspacePath.get_by_id(workspace_path.id)
        assert updated_path.hiding_rules == new_rules

    def test_update_hiding_rules_nonexistent_path(self, sample_workspace):
        """Test updating hiding rules for non-existent path returns False."""
        success = WorkspacePath.update_hiding_rules(99999, r".*\.tmp")
        assert not success

    def test_get_paths_for_workspace_includes_hiding_rules(self, sample_workspace):
        """Test that get_paths_for_workspace returns paths with hiding rules."""
        rules1 = r".*\.tmp;.*\.log"
        rules2 = r"node_modules;dist/"

        path1 = WorkspacePath.add_path(sample_workspace.id, "/path1", "folder", rules1, check_existence=False)
        path2 = WorkspacePath.add_path(sample_workspace.id, "/path2", "folder", rules2, check_existence=False)

        paths = WorkspacePath.get_paths_for_workspace(sample_workspace.id)
        assert len(paths) == 2

        # Find our paths in the results
        path_dict = {p.root_path: p for p in paths}

        assert path_dict["/path1"].hiding_rules == rules1
        assert path_dict["/path2"].hiding_rules == rules2

    def test_workspace_path_to_dict_includes_hiding_rules(self, sample_workspace):
        """Test that WorkspacePath.to_dict() includes hiding_rules field."""
        hiding_rules = r".*\.tmp;.*\.log;cache/"
        workspace_path = WorkspacePath.add_path(
            sample_workspace.id,
            "/path/to/folder",
            "folder",
            hiding_rules,
            check_existence=False
        )

        path_dict = workspace_path.to_dict()
        assert "hiding_rules" in path_dict
        assert path_dict["hiding_rules"] == hiding_rules