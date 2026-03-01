"""
Database initialization and connection management for Workspace File Indexer.

This module handles the SQLite database setup and provides connection utilities
for the core data layer.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime


def get_db_path():
    """Get the path to the SQLite database file."""
    # Create a data directory in the user's home directory
    data_dir = Path.home() / '.workspace_indexer'
    data_dir.mkdir(exist_ok=True)
    return data_dir / 'workspace_indexer.db'


def get_connection():
    """Get a connection to the SQLite database."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
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
                FOREIGN KEY (workspace_id) REFERENCES workspace (id) ON DELETE CASCADE,
                UNIQUE(workspace_id, root_path)
            )
        ''')

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
        print(f"Database initialized successfully at: {get_db_path()}")

    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
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
            print(f"Missing tables: {missing_tables}")
            return False

        print("Database verification successful - all required tables exist")
        return True

    except sqlite3.Error as e:
        print(f"Error verifying database: {e}")
        return False
    finally:
        conn.close()


if __name__ == '__main__':
    # Initialize database when run directly
    initialize_database()
    verify_database()