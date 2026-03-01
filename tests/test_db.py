"""
Unit tests for database initialization and schema validation.

Tests verify that the database file is created correctly and all tables
match the specification exactly.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

# Import from parent directory
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.db import initialize_database, verify_database, get_connection, get_db_path


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""

    def setup_method(self):
        """Setup for each test method."""
        # Use a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = Path(self.test_dir) / 'test_workspace_indexer.db'

    def teardown_method(self):
        """Cleanup after each test method."""
        # Remove test database if it exists
        if self.test_db_path.exists():
            os.unlink(self.test_db_path)
        os.rmdir(self.test_dir)

    @patch('core.db.get_db_path')
    def test_database_file_creation(self, mock_get_db_path):
        """Test that database file is created correctly."""
        mock_get_db_path.return_value = self.test_db_path

        # Database file should not exist initially
        assert not self.test_db_path.exists()

        # Initialize database
        initialize_database()

        # Database file should now exist
        assert self.test_db_path.exists()

    @patch('core.db.get_db_path')
    def test_workspace_table_schema(self, mock_get_db_path):
        """Test that workspace table has correct schema."""
        mock_get_db_path.return_value = self.test_db_path

        initialize_database()

        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        # Get table schema
        cursor.execute("PRAGMA table_info(workspace)")
        columns = cursor.fetchall()
        conn.close()

        # Verify column structure
        expected_columns = {
            'id': ('INTEGER', 0, None, 1),  # (type, notnull, default, pk) - PK columns don't show NOT NULL explicitly
            'name': ('TEXT', 1, None, 0),
            'created_at': ('TEXT', 1, None, 0)
        }

        assert len(columns) == len(expected_columns)
        for col in columns:
            col_name = col[1]
            assert col_name in expected_columns
            expected = expected_columns[col_name]
            assert col[2] == expected[0]  # type
            assert col[3] == expected[1]  # not null
            assert col[5] == expected[3]  # primary key

    @patch('core.db.get_db_path')
    def test_workspace_path_table_schema(self, mock_get_db_path):
        """Test that workspace_path table has correct schema."""
        mock_get_db_path.return_value = self.test_db_path

        initialize_database()

        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        # Get table schema
        cursor.execute("PRAGMA table_info(workspace_path)")
        columns = cursor.fetchall()
        conn.close()

        # Verify column structure
        expected_columns = {
            'id': ('INTEGER', 1, None, 1),
            'workspace_id': ('INTEGER', 1, None, 0),
            'root_path': ('TEXT', 1, None, 0),
            'type': ('TEXT', 1, None, 0)
        }

        assert len(columns) == len(expected_columns)
        for col in columns:
            col_name = col[1]
            assert col_name in expected_columns

    @patch('core.db.get_db_path')
    def test_file_entry_table_schema(self, mock_get_db_path):
        """Test that file_entry table has correct schema."""
        mock_get_db_path.return_value = self.test_db_path

        initialize_database()

        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        # Get table schema
        cursor.execute("PRAGMA table_info(file_entry)")
        columns = cursor.fetchall()
        conn.close()

        # Verify column structure
        expected_columns = {
            'id': ('INTEGER', 1, None, 1),
            'workspace_id': ('INTEGER', 1, None, 0),
            'relative_path': ('TEXT', 1, None, 0),
            'absolute_path': ('TEXT', 1, None, 0),
            'file_type': ('TEXT', 0, None, 0)
        }

        assert len(columns) == len(expected_columns)
        for col in columns:
            col_name = col[1]
            assert col_name in expected_columns

    @patch('core.db.get_db_path')
    def test_tags_table_schema(self, mock_get_db_path):
        """Test that tags table has correct schema."""
        mock_get_db_path.return_value = self.test_db_path

        initialize_database()

        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        # Get table schema
        cursor.execute("PRAGMA table_info(tags)")
        columns = cursor.fetchall()
        conn.close()

        # Verify column structure
        expected_columns = {
            'id': ('INTEGER', 1, None, 1),
            'file_id': ('INTEGER', 1, None, 0),
            'tag_name': ('TEXT', 1, None, 0)
        }

        assert len(columns) == len(expected_columns)
        for col in columns:
            col_name = col[1]
            assert col_name in expected_columns

    @patch('core.db.get_db_path')
    def test_all_required_tables_exist(self, mock_get_db_path):
        """Test that all required tables are created."""
        mock_get_db_path.return_value = self.test_db_path

        initialize_database()

        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Verify all required tables exist
        required_tables = {'workspace', 'workspace_path', 'file_entry', 'tags'}
        existing_tables = set(tables)

        assert required_tables.issubset(existing_tables)

    @patch('core.db.get_db_path')
    def test_foreign_key_constraints(self, mock_get_db_path):
        """Test that foreign key constraints are properly defined."""
        mock_get_db_path.return_value = self.test_db_path

        initialize_database()

        conn = sqlite3.connect(str(self.test_db_path))
        cursor = conn.cursor()

        # Check workspace_path foreign key
        cursor.execute("PRAGMA foreign_key_list(workspace_path)")
        fk_constraints = cursor.fetchall()
        assert len(fk_constraints) == 1
        assert fk_constraints[0][2] == 'workspace'  # references workspace table
        assert fk_constraints[0][3] == 'workspace_id'  # from column
        assert fk_constraints[0][4] == 'id'  # to column

        # Check file_entry foreign key
        cursor.execute("PRAGMA foreign_key_list(file_entry)")
        fk_constraints = cursor.fetchall()
        assert len(fk_constraints) == 1

        # Check tags foreign key
        cursor.execute("PRAGMA foreign_key_list(tags)")
        fk_constraints = cursor.fetchall()
        assert len(fk_constraints) == 1

        conn.close()

    @patch('core.db.get_db_path')
    def test_verify_database_success(self, mock_get_db_path):
        """Test that database verification works correctly."""
        mock_get_db_path.return_value = self.test_db_path

        initialize_database()

        # Verification should succeed
        assert verify_database() is True

    @patch('core.db.get_db_path')
    def test_verify_database_failure(self, mock_get_db_path):
        """Test that database verification fails for incomplete database."""
        mock_get_db_path.return_value = self.test_db_path

        # Create database file but don't initialize schema
        conn = sqlite3.connect(str(self.test_db_path))
        conn.close()

        # Verification should fail
        assert verify_database() is False