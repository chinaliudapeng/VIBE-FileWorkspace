"""
Unit tests for Tag model CRUD operations.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from core.models import Tag, Workspace, WorkspacePath
from core.db import initialize_database, get_connection


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
def sample_data(temp_db):
    """Create sample workspace and file entry data for testing."""
    # Create a workspace
    workspace = Workspace.create("Test Workspace")

    # Add a workspace path
    workspace_path = WorkspacePath.add_path(workspace.id, "/test/path", "folder")

    # Manually insert file entries since FileEntry model doesn't exist yet
    conn = get_connection()
    cursor = conn.cursor()

    # Insert test file entries
    cursor.execute('''
        INSERT INTO file_entry (workspace_id, relative_path, absolute_path, file_type)
        VALUES (?, ?, ?, ?)
    ''', (workspace.id, "file1.py", "/test/path/file1.py", "python"))

    file1_id = cursor.lastrowid

    cursor.execute('''
        INSERT INTO file_entry (workspace_id, relative_path, absolute_path, file_type)
        VALUES (?, ?, ?, ?)
    ''', (workspace.id, "file2.js", "/test/path/file2.js", "javascript"))

    file2_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        'workspace': workspace,
        'file1_id': file1_id,
        'file2_id': file2_id
    }


class TestTagModel:
    """Test cases for Tag model."""

    def test_add_tag_to_file_success(self, temp_db, sample_data):
        """Test successfully adding a tag to a file."""
        file_id = sample_data['file1_id']
        tag = Tag.add_tag_to_file(file_id, "bug")

        assert tag.id is not None
        assert tag.file_id == file_id
        assert tag.tag_name == "bug"

    def test_add_tag_to_file_strips_whitespace(self, temp_db, sample_data):
        """Test that adding a tag strips whitespace."""
        file_id = sample_data['file1_id']
        tag = Tag.add_tag_to_file(file_id, "  urgent  ")

        assert tag.tag_name == "urgent"

    def test_add_tag_to_file_empty_name_fails(self, temp_db, sample_data):
        """Test that adding an empty tag name fails."""
        file_id = sample_data['file1_id']

        with pytest.raises(ValueError, match="tag_name cannot be empty"):
            Tag.add_tag_to_file(file_id, "")

        with pytest.raises(ValueError, match="tag_name cannot be empty"):
            Tag.add_tag_to_file(file_id, "   ")

    def test_add_tag_to_nonexistent_file_fails(self, temp_db, sample_data):
        """Test that adding a tag to a nonexistent file fails."""
        nonexistent_file_id = 9999

        with pytest.raises(ValueError, match=f"File with ID {nonexistent_file_id} does not exist"):
            Tag.add_tag_to_file(nonexistent_file_id, "test")

    def test_add_duplicate_tag_fails(self, temp_db, sample_data):
        """Test that adding a duplicate tag to the same file fails."""
        file_id = sample_data['file1_id']

        # Add the first tag
        Tag.add_tag_to_file(file_id, "duplicate")

        # Try to add the same tag again
        with pytest.raises(sqlite3.IntegrityError):
            Tag.add_tag_to_file(file_id, "duplicate")

    def test_remove_tag_from_file_success(self, temp_db, sample_data):
        """Test successfully removing a tag from a file."""
        file_id = sample_data['file1_id']

        # Add a tag first
        Tag.add_tag_to_file(file_id, "removeme")

        # Remove the tag
        success = Tag.remove_tag_from_file(file_id, "removeme")
        assert success is True

    def test_remove_tag_from_file_strips_whitespace(self, temp_db, sample_data):
        """Test that removing a tag strips whitespace."""
        file_id = sample_data['file1_id']

        # Add a tag
        Tag.add_tag_to_file(file_id, "spacetest")

        # Remove the tag with spaces
        success = Tag.remove_tag_from_file(file_id, "  spacetest  ")
        assert success is True

    def test_remove_nonexistent_tag_returns_false(self, temp_db, sample_data):
        """Test that removing a nonexistent tag returns False."""
        file_id = sample_data['file1_id']

        success = Tag.remove_tag_from_file(file_id, "nonexistent")
        assert success is False

    def test_remove_tag_by_id_success(self, temp_db, sample_data):
        """Test successfully removing a tag by ID."""
        file_id = sample_data['file1_id']

        # Add a tag first
        tag = Tag.add_tag_to_file(file_id, "removeme")

        # Remove by ID
        success = Tag.remove_tag_by_id(tag.id)
        assert success is True

    def test_remove_tag_by_nonexistent_id_returns_false(self, temp_db, sample_data):
        """Test that removing a tag by nonexistent ID returns False."""
        success = Tag.remove_tag_by_id(9999)
        assert success is False

    def test_get_tags_for_file_success(self, temp_db, sample_data):
        """Test getting all tags for a file."""
        file_id = sample_data['file1_id']

        # Add multiple tags
        Tag.add_tag_to_file(file_id, "bug")
        Tag.add_tag_to_file(file_id, "urgent")
        Tag.add_tag_to_file(file_id, "api")

        # Get tags (should be ordered alphabetically)
        tags = Tag.get_tags_for_file(file_id)

        assert len(tags) == 3
        assert tags[0].tag_name == "api"
        assert tags[1].tag_name == "bug"
        assert tags[2].tag_name == "urgent"

        # Verify all tags have correct file_id
        for tag in tags:
            assert tag.file_id == file_id
            assert tag.id is not None

    def test_get_tags_for_file_empty_returns_empty_list(self, temp_db, sample_data):
        """Test getting tags for a file with no tags returns empty list."""
        file_id = sample_data['file1_id']

        tags = Tag.get_tags_for_file(file_id)
        assert tags == []

    def test_get_all_unique_tags_success(self, temp_db, sample_data):
        """Test getting all unique tags in the database."""
        file1_id = sample_data['file1_id']
        file2_id = sample_data['file2_id']

        # Add tags to different files (some duplicates)
        Tag.add_tag_to_file(file1_id, "bug")
        Tag.add_tag_to_file(file1_id, "urgent")
        Tag.add_tag_to_file(file2_id, "bug")  # duplicate
        Tag.add_tag_to_file(file2_id, "feature")

        # Get unique tags (should be ordered alphabetically)
        unique_tags = Tag.get_all_unique_tags()

        assert len(unique_tags) == 3
        assert unique_tags == ["bug", "feature", "urgent"]

    def test_get_all_unique_tags_empty_database(self, temp_db, sample_data):
        """Test getting unique tags from empty database returns empty list."""
        unique_tags = Tag.get_all_unique_tags()
        assert unique_tags == []

    def test_get_by_id_success(self, temp_db, sample_data):
        """Test getting a tag by ID."""
        file_id = sample_data['file1_id']

        # Add a tag
        original_tag = Tag.add_tag_to_file(file_id, "findme")

        # Get by ID
        found_tag = Tag.get_by_id(original_tag.id)

        assert found_tag is not None
        assert found_tag.id == original_tag.id
        assert found_tag.file_id == file_id
        assert found_tag.tag_name == "findme"

    def test_get_by_nonexistent_id_returns_none(self, temp_db, sample_data):
        """Test getting a tag by nonexistent ID returns None."""
        tag = Tag.get_by_id(9999)
        assert tag is None

    def test_tag_exists_for_file_true(self, temp_db, sample_data):
        """Test checking if a tag exists for a file returns True when it exists."""
        file_id = sample_data['file1_id']

        # Add a tag
        Tag.add_tag_to_file(file_id, "exists")

        # Check if it exists
        exists = Tag.tag_exists_for_file(file_id, "exists")
        assert exists is True

    def test_tag_exists_for_file_false(self, temp_db, sample_data):
        """Test checking if a tag exists for a file returns False when it doesn't exist."""
        file_id = sample_data['file1_id']

        exists = Tag.tag_exists_for_file(file_id, "nonexistent")
        assert exists is False

    def test_tag_exists_for_file_strips_whitespace(self, temp_db, sample_data):
        """Test that tag existence check strips whitespace."""
        file_id = sample_data['file1_id']

        # Add a tag
        Tag.add_tag_to_file(file_id, "trimtest")

        # Check with spaces
        exists = Tag.tag_exists_for_file(file_id, "  trimtest  ")
        assert exists is True

    def test_to_dict(self, temp_db, sample_data):
        """Test converting tag to dictionary."""
        file_id = sample_data['file1_id']

        # Add a tag
        tag = Tag.add_tag_to_file(file_id, "dicttest")

        # Convert to dict
        tag_dict = tag.to_dict()

        expected_dict = {
            'id': tag.id,
            'file_id': file_id,
            'tag_name': 'dicttest'
        }

        assert tag_dict == expected_dict

    def test_str_and_repr(self, temp_db, sample_data):
        """Test string representation of tag."""
        file_id = sample_data['file1_id']

        # Add a tag
        tag = Tag.add_tag_to_file(file_id, "stringtest")

        expected_str = f"Tag(id={tag.id}, file_id={file_id}, tag_name='stringtest')"
        assert str(tag) == expected_str
        assert repr(tag) == expected_str

    def test_foreign_key_cascade_delete(self, temp_db, sample_data):
        """Test that tags are deleted when file_entry is deleted (cascade)."""
        file1_id = sample_data['file1_id']

        # Add tags to the file
        Tag.add_tag_to_file(file1_id, "tag1")
        Tag.add_tag_to_file(file1_id, "tag2")

        # Verify tags exist
        tags = Tag.get_tags_for_file(file1_id)
        assert len(tags) == 2

        # Delete the file entry
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM file_entry WHERE id = ?', (file1_id,))
        conn.commit()
        conn.close()

        # Verify tags are also deleted
        tags = Tag.get_tags_for_file(file1_id)
        assert len(tags) == 0