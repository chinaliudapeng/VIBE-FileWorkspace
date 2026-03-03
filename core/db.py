"""
Database initialization and connection management for Workspace File Indexer.

This module handles the SQLite database setup and provides connection utilities
for the core data layer.
"""

import sqlite3
import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
from .logging_config import get_logger

logger = get_logger('db')


def _get_application_root():
    """Get the root directory of the application."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller executable
        return Path(sys.executable).parent
    else:
        # Running from source code (development mode)
        # Find the project root by looking for the main script files
        current_dir = Path(__file__).parent
        project_root = current_dir.parent  # Go up from core/ to project root
        return project_root


def _get_legacy_db_path():
    """Get the legacy database path (user home directory)."""
    data_dir = Path.home() / '.workspace_indexer'
    return data_dir / 'workspace_indexer.db'


def get_db_path():
    """Get the path to the SQLite database file."""
    app_root = _get_application_root()

    if getattr(sys, 'frozen', False):
        # Running as executable: use .db directory next to exe
        data_dir = app_root / '.db'
        data_dir.mkdir(exist_ok=True)
        new_db_path = data_dir / 'workspace_indexer.db'

        # Check if migration is needed from legacy location
        legacy_db_path = _get_legacy_db_path()
        if legacy_db_path.exists() and not new_db_path.exists():
            _migrate_database_from_legacy(legacy_db_path, new_db_path)

        return new_db_path
    else:
        # Running from source: use legacy location for development
        data_dir = Path.home() / '.workspace_indexer'
        data_dir.mkdir(exist_ok=True)
        return data_dir / 'workspace_indexer.db'


def _migrate_database_from_legacy(legacy_path, new_path):
    """Migrate database from legacy location to new location."""
    try:
        logger.info(f"Migrating database from {legacy_path} to {new_path}")

        # Ensure target directory exists
        new_path.parent.mkdir(exist_ok=True)

        # Copy the database file
        shutil.copy2(legacy_path, new_path)
        logger.info(f"Database migrated successfully to {new_path}")

        # Verify the migration worked by testing a connection
        test_conn = sqlite3.connect(str(new_path))
        test_conn.execute('PRAGMA foreign_keys = ON')
        test_conn.close()
        logger.info("Migration verification successful")

        # Remove the legacy database and directory if possible
        try:
            legacy_path.unlink()
            logger.info(f"Removed legacy database file: {legacy_path}")

            # Try to remove the legacy directory if it's empty
            legacy_dir = legacy_path.parent
            if legacy_dir.exists() and not any(legacy_dir.iterdir()):
                legacy_dir.rmdir()
                logger.info(f"Removed empty legacy directory: {legacy_dir}")
        except OSError as e:
            logger.warning(f"Could not remove legacy database files: {e}")

    except Exception as e:
        logger.error(f"Error migrating database from {legacy_path} to {new_path}: {e}")
        raise


def get_connection():
    """Get a connection to the SQLite database."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
    conn.execute('PRAGMA foreign_keys = ON')  # Enable foreign key constraints
    return conn


def initialize_database():
    """
    Initialize the database with the required schema.

    Creates all tables according to the specification:
    - workspace: id, name, created_at
    - workspace_path: id, workspace_id, root_path, type (folder/file)
    - file_entry: id, workspace_id, relative_path, absolute_path, file_type
    - tags: id, file_id, tag_name
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Create workspace table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workspace (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        ''')

        # Create workspace_path table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workspace_path (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                root_path TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('folder', 'file')),
                hiding_rules TEXT DEFAULT '',
                FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE,
                UNIQUE(workspace_id, root_path)
            )
        ''')

        # Add hiding_rules column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE workspace_path ADD COLUMN hiding_rules TEXT DEFAULT ""')
            logger.info("Added hiding_rules column to workspace_path table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                logger.error(f"Error adding hiding_rules column: {e}")
                raise
            else:
                logger.debug("hiding_rules column already exists in workspace_path table")

        # Create file_entry table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_entry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                relative_path TEXT NOT NULL,
                absolute_path TEXT NOT NULL UNIQUE,
                file_type TEXT,
                FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE
            )
        ''')

        # Create tags table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                tag_name TEXT NOT NULL,
                FOREIGN KEY (file_id) REFERENCES file_entry (id) ON DELETE CASCADE,
                UNIQUE(file_id, tag_name)
            )
        ''')

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_workspace_path_workspace_id ON workspace_path(workspace_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_entry_workspace_id ON file_entry(workspace_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_entry_absolute_path ON file_entry(absolute_path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_file_id ON tags(file_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags_tag_name ON tags(tag_name)')

        conn.commit()
        logger.info(f"Database initialized successfully at: {get_db_path()}")

    except sqlite3.Error as e:
        logger.error(f"Error initializing database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_database():
    """
    Verify that the database exists and has all required tables.

    Returns:
        bool: True if database is properly initialized, False otherwise.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check that all required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        required_tables = {'workspace', 'workspace_path', 'file_entry', 'tags'}
        existing_tables = set(tables)

        missing_tables = required_tables - existing_tables
        if missing_tables:
            logger.error(f"Missing tables: {missing_tables}")
            return False

        logger.info("Database verification successful - all required tables exist")
        return True

    except sqlite3.Error as e:
        logger.error(f"Error verifying database: {e}")
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    # Initialize database when run directly
    initialize_database()
    verify_database()