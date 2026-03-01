"""
Unit tests for Workspace model CRUD operations.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

from core.models import Workspace
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


class TestWorkspaceModel:
    """Test cases for Workspace model."""

    def test_create_workspace_success(self, temp_db):
        """Test successfully creating a workspace."""
        workspace = Workspace.create("Test Workspace")

        assert workspace.id is not None
        assert workspace.name == "Test Workspace"
        assert workspace.created_at is not None

        # Verify timestamp format
        datetime.fromisoformat(workspace.created_at)  # Should not raise

    def test_create_workspace_duplicate_name_fails(self, temp_db):
        """Test that creating a workspace with duplicate name fails."""
        Workspace.create("Duplicate Name")

        with pytest.raises(sqlite3.IntegrityError):
            Workspace.create("Duplicate Name")

    def test_create_workspace_empty_name_fails(self, temp_db):
        """Test that creating a workspace with empty name fails."""
        with pytest.raises(ValueError, match="Workspace name cannot be empty"):
            Workspace.create("")

    def test_create_workspace_whitespace_name_fails(self, temp_db):
        """Test that creating a workspace with whitespace-only name fails."""
        with pytest.raises(ValueError, match="Workspace name cannot be empty"):
            Workspace.create("   \t\n   ")

    def test_list_all_workspaces_empty(self, temp_db):
        """Test listing workspaces when database is empty."""
        workspaces = Workspace.list_all()
        assert workspaces == []

    def test_list_all_workspaces_with_data(self, temp_db):
        """Test listing workspaces when database has data."""
        # Create test workspaces
        workspace1 = Workspace.create("Alpha Workspace")
        workspace2 = Workspace.create("Beta Workspace")
        workspace3 = Workspace.create("Gamma Workspace")

        workspaces = Workspace.list_all()

        # Should be ordered by name alphabetically
        assert len(workspaces) == 3
        assert workspaces[0].name == "Alpha Workspace"
        assert workspaces[1].name == "Beta Workspace"
        assert workspaces[2].name == "Gamma Workspace"

        # Verify all properties are set
        for workspace in workspaces:
            assert workspace.id is not None
            assert workspace.name != ""
            assert workspace.created_at is not None

    def test_get_by_id_success(self, temp_db):
        """Test successfully retrieving workspace by ID."""
        created_workspace = Workspace.create("Test Workspace")

        retrieved_workspace = Workspace.get_by_id(created_workspace.id)

        assert retrieved_workspace is not None
        assert retrieved_workspace.id == created_workspace.id
        assert retrieved_workspace.name == "Test Workspace"
        assert retrieved_workspace.created_at == created_workspace.created_at

    def test_get_by_id_not_found(self, temp_db):
        """Test retrieving workspace by non-existent ID."""
        workspace = Workspace.get_by_id(99999)
        assert workspace is None

    def test_get_by_name_success(self, temp_db):
        """Test successfully retrieving workspace by name."""
        created_workspace = Workspace.create("Unique Name")

        retrieved_workspace = Workspace.get_by_name("Unique Name")

        assert retrieved_workspace is not None
        assert retrieved_workspace.id == created_workspace.id
        assert retrieved_workspace.name == "Unique Name"
        assert retrieved_workspace.created_at == created_workspace.created_at

    def test_get_by_name_not_found(self, temp_db):
        """Test retrieving workspace by non-existent name."""
        workspace = Workspace.get_by_name("Non-existent Workspace")
        assert workspace is None

    def test_delete_workspace_success(self, temp_db):
        """Test successfully deleting a workspace."""
        workspace = Workspace.create("To Be Deleted")
        workspace_id = workspace.id

        # Delete the workspace
        result = Workspace.delete(workspace_id)
        assert result is True

        # Verify it's gone
        retrieved_workspace = Workspace.get_by_id(workspace_id)
        assert retrieved_workspace is None

    def test_delete_workspace_not_found(self, temp_db):
        """Test deleting a non-existent workspace."""
        result = Workspace.delete(99999)
        assert result is False

    def test_update_workspace_success(self, temp_db):
        """Test successfully updating a workspace name."""
        workspace = Workspace.create("Original Name")
        original_id = workspace.id
        original_created_at = workspace.created_at

        workspace.update("Updated Name")

        assert workspace.name == "Updated Name"
        assert workspace.id == original_id
        assert workspace.created_at == original_created_at

        # Verify in database
        retrieved_workspace = Workspace.get_by_id(original_id)
        assert retrieved_workspace.name == "Updated Name"

    def test_update_workspace_duplicate_name_fails(self, temp_db):
        """Test updating workspace to duplicate name fails."""
        workspace1 = Workspace.create("First Workspace")
        workspace2 = Workspace.create("Second Workspace")

        with pytest.raises(sqlite3.IntegrityError):
            workspace2.update("First Workspace")

    def test_update_workspace_without_id_fails(self, temp_db):
        """Test updating workspace without ID fails."""
        workspace = Workspace(name="No ID Workspace")

        with pytest.raises(ValueError, match="Cannot update workspace without ID"):
            workspace.update("New Name")

    def test_workspace_to_dict(self, temp_db):
        """Test converting workspace to dictionary."""
        workspace = Workspace.create("Dict Test")

        workspace_dict = workspace.to_dict()

        assert isinstance(workspace_dict, dict)
        assert workspace_dict['id'] == workspace.id
        assert workspace_dict['name'] == "Dict Test"
        assert workspace_dict['created_at'] == workspace.created_at

    def test_workspace_str_representation(self, temp_db):
        """Test string representation of workspace."""
        workspace = Workspace.create("String Test")

        str_repr = str(workspace)

        assert "Workspace(" in str_repr
        assert "String Test" in str_repr
        assert str(workspace.id) in str_repr

    def test_workspace_constructor(self, temp_db):
        """Test workspace constructor with different parameters."""
        # Test with all parameters
        workspace1 = Workspace(id=1, name="Test", created_at="2024-01-01T00:00:00")
        assert workspace1.id == 1
        assert workspace1.name == "Test"
        assert workspace1.created_at == "2024-01-01T00:00:00"

        # Test with automatic timestamp
        workspace2 = Workspace(name="Auto Timestamp")
        assert workspace2.id is None
        assert workspace2.name == "Auto Timestamp"
        assert workspace2.created_at is not None
        # Should be able to parse the timestamp
        datetime.fromisoformat(workspace2.created_at)