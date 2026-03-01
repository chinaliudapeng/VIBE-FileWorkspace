"""
Data models and CRUD operations for Workspace File Indexer.

This module provides the core data layer for managing workspaces, workspace paths,
file entries, and tags. All database operations should go through this module
to maintain a single source of truth.
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from .db import get_connection


class Workspace:
    """Model for workspace data and operations."""

    def __init__(self, id: Optional[int] = None, name: str = "", created_at: Optional[str] = None):
        self.id = id
        self.name = name
        self.created_at = created_at or datetime.now().isoformat()

    @classmethod
    def create(cls, name: str) -> 'Workspace':
        """
        Create a new workspace in the database.

        Args:
            name: The workspace name (must be unique and non-empty)

        Returns:
            Workspace: The created workspace with ID populated

        Raises:
            ValueError: If workspace name is empty or whitespace-only
            sqlite3.IntegrityError: If workspace name already exists
        """
        # Validate name is not empty or whitespace-only
        if not name or not name.strip():
            raise ValueError("Workspace name cannot be empty")

        conn = get_connection()
        try:
            cursor = conn.cursor()
            created_at = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO workspace (name, created_at)
                VALUES (?, ?)
            ''', (name.strip(), created_at))

            workspace_id = cursor.lastrowid
            conn.commit()

            return cls(id=workspace_id, name=name.strip(), created_at=created_at)

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def list_all(cls) -> List['Workspace']:
        """
        Retrieve all workspaces from the database.

        Returns:
            List[Workspace]: List of all workspaces ordered by name
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, created_at
                FROM workspace
                ORDER BY name ASC
            ''')

            workspaces = []
            for row in cursor.fetchall():
                workspace = cls(
                    id=row['id'],
                    name=row['name'],
                    created_at=row['created_at']
                )
                workspaces.append(workspace)

            return workspaces

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, workspace_id: int) -> Optional['Workspace']:
        """
        Retrieve a workspace by its ID.

        Args:
            workspace_id: The workspace ID

        Returns:
            Workspace: The workspace if found, None otherwise
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, created_at
                FROM workspace
                WHERE id = ?
            ''', (workspace_id,))

            row = cursor.fetchone()
            if row:
                return cls(
                    id=row['id'],
                    name=row['name'],
                    created_at=row['created_at']
                )
            return None

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Workspace']:
        """
        Retrieve a workspace by its name.

        Args:
            name: The workspace name

        Returns:
            Workspace: The workspace if found, None otherwise
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, name, created_at
                FROM workspace
                WHERE name = ?
            ''', (name,))

            row = cursor.fetchone()
            if row:
                return cls(
                    id=row['id'],
                    name=row['name'],
                    created_at=row['created_at']
                )
            return None

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def delete(cls, workspace_id: int) -> bool:
        """
        Delete a workspace and all associated data.

        Due to CASCADE DELETE foreign key constraints, this will also remove:
        - All workspace_path entries
        - All file_entry entries
        - All tags entries

        Args:
            workspace_id: The workspace ID to delete

        Returns:
            bool: True if workspace was deleted, False if not found
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Check if workspace exists first
            cursor.execute('SELECT id FROM workspace WHERE id = ?', (workspace_id,))
            if not cursor.fetchone():
                return False

            # Delete the workspace (cascades to related tables)
            cursor.execute('DELETE FROM workspace WHERE id = ?', (workspace_id,))
            conn.commit()

            return True

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update(self, new_name: str) -> None:
        """
        Update the workspace name.

        Args:
            new_name: The new workspace name

        Raises:
            sqlite3.IntegrityError: If new name already exists
            ValueError: If workspace ID is not set
        """
        if not self.id:
            raise ValueError("Cannot update workspace without ID")

        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE workspace
                SET name = ?
                WHERE id = ?
            ''', (new_name, self.id))

            if cursor.rowcount == 0:
                raise ValueError(f"Workspace with ID {self.id} not found")

            conn.commit()
            self.name = new_name

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert workspace to dictionary representation.

        Returns:
            dict: Dictionary with workspace data
        """
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at
        }

    def __str__(self) -> str:
        return f"Workspace(id={self.id}, name='{self.name}', created_at='{self.created_at}')"

    def __repr__(self) -> str:
        return self.__str__()