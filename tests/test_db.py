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

from core.db import initialize_database, verify_database, get_connection, get_db_path, _get_application_root, _migrate_database_from_legacy


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
            'type': ('TEXT', 1, None, 0),
            'hiding_rules': ('TEXT', 0, "''", 0)
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


class TestDatabaseMigration:
    """Test database migration functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Use temporary directories for tests
        self.test_dir = tempfile.mkdtemp()
        self.legacy_db_path = Path(self.test_dir) / 'legacy' / 'workspace_indexer.db'
        self.new_db_path = Path(self.test_dir) / 'new' / 'workspace_indexer.db'

        # Create directories
        self.legacy_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.new_db_path.parent.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Cleanup after each test method."""
        # Remove test directories
        import shutil
        shutil.rmtree(self.test_dir)

    def test_migrate_database_from_legacy(self):
        """Test successful database migration."""
        # Create a legacy database with some data
        conn = sqlite3.connect(str(self.legacy_db_path))
        conn.execute('CREATE TABLE test_table (id INTEGER, name TEXT)')
        conn.execute('INSERT INTO test_table VALUES (1, "test")')
        conn.commit()
        conn.close()

        # Migrate the database
        _migrate_database_from_legacy(self.legacy_db_path, self.new_db_path)

        # Verify migration worked
        assert self.new_db_path.exists()

        # Check data was copied correctly
        conn = sqlite3.connect(str(self.new_db_path))
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM test_table')
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0] == (1, 'test')

    def test_migrate_database_removes_legacy_file(self):
        """Test that legacy database file is removed after successful migration."""
        # Create a legacy database
        conn = sqlite3.connect(str(self.legacy_db_path))
        conn.execute('CREATE TABLE test_table (id INTEGER)')
        conn.close()

        # Migrate the database
        _migrate_database_from_legacy(self.legacy_db_path, self.new_db_path)

        # Verify legacy file is removed
        assert not self.legacy_db_path.exists()
        assert self.new_db_path.exists()

    @patch('sys.frozen', True, create=True)
    @patch('sys.executable')
    def test_get_db_path_executable_mode(self, mock_executable):
        """Test database path in executable mode."""
        # Mock the executable path
        exe_dir = Path(self.test_dir) / 'exe_dir'
        exe_dir.mkdir()
        mock_executable = str(exe_dir / 'app.exe')

        # Mock sys.executable to return our test path
        with patch('sys.executable', mock_executable):
            db_path = get_db_path()
            expected_path = exe_dir / '.db' / 'workspace_indexer.db'
            assert db_path == expected_path

    @patch('sys.frozen', False, create=True)
    def test_get_db_path_development_mode(self):
        """Test database path in development mode (running from source)."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path(self.test_dir) / 'home'
            mock_home.return_value.mkdir()

            db_path = get_db_path()
            expected_path = mock_home.return_value / '.workspace_indexer' / 'workspace_indexer.db'
            assert db_path == expected_path

    @patch('sys.frozen', True, create=True)
    @patch('sys.executable')
    def test_get_db_path_with_migration(self, mock_executable):
        """Test database path with automatic migration from legacy location."""
        exe_dir = Path(self.test_dir) / 'exe_dir'
        exe_dir.mkdir()
        mock_executable = str(exe_dir / 'app.exe')

        # Create a legacy database
        legacy_dir = Path(self.test_dir) / 'legacy_home' / '.workspace_indexer'
        legacy_dir.mkdir(parents=True)
        legacy_db = legacy_dir / 'workspace_indexer.db'

        conn = sqlite3.connect(str(legacy_db))
        conn.execute('CREATE TABLE test_table (id INTEGER)')
        conn.close()

        with patch('sys.executable', mock_executable):
            with patch('core.db._get_legacy_db_path', return_value=legacy_db):
                db_path = get_db_path()

                # Should return new path
                expected_path = exe_dir / '.db' / 'workspace_indexer.db'
                assert db_path == expected_path

                # New database should exist and contain data
                assert expected_path.exists()

                conn = sqlite3.connect(str(expected_path))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()

                assert len(tables) >= 1  # Should have at least the test_table