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

            # Stop filesystem watcher for this workspace before deletion
            try:
                from . import watcher
                watcher.stop_watching_workspace(workspace_id)
            except Exception:
                # Don't fail the delete if watcher cleanup fails
                pass

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


class WorkspacePath:
    """Model for workspace path data and operations."""

    def __init__(self, id: Optional[int] = None, workspace_id: int = 0,
                 root_path: str = "", path_type: str = "folder"):
        self.id = id
        self.workspace_id = workspace_id
        self.root_path = root_path
        self.path_type = path_type  # 'folder' or 'file'

    @classmethod
    def add_path(cls, workspace_id: int, root_path: str, path_type: str) -> 'WorkspacePath':
        """
        Add a path to a workspace.

        Args:
            workspace_id: The workspace ID
            root_path: The absolute path to the folder or file
            path_type: 'folder' or 'file'

        Returns:
            WorkspacePath: The created workspace path

        Raises:
            ValueError: If workspace_id doesn't exist or path_type is invalid
            sqlite3.IntegrityError: If path already exists for this workspace
        """
        # Validate path_type
        if path_type not in ('folder', 'file'):
            raise ValueError("path_type must be 'folder' or 'file'")

        # Validate root_path is not empty
        if not root_path or not root_path.strip():
            raise ValueError("root_path cannot be empty")

        root_path = root_path.strip()

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Verify workspace exists
            cursor.execute('SELECT id FROM workspace WHERE id = ?', (workspace_id,))
            if not cursor.fetchone():
                raise ValueError(f"Workspace with ID {workspace_id} does not exist")

            # Insert the workspace path
            cursor.execute('''
                INSERT INTO workspace_path (workspace_id, root_path, type)
                VALUES (?, ?, ?)
            ''', (workspace_id, root_path, path_type))

            path_id = cursor.lastrowid
            conn.commit()

            return cls(id=path_id, workspace_id=workspace_id,
                      root_path=root_path, path_type=path_type)

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def remove_path(cls, workspace_id: int, root_path: str) -> bool:
        """
        Remove a path from a workspace.

        Args:
            workspace_id: The workspace ID
            root_path: The path to remove

        Returns:
            bool: True if path was removed, False if not found
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM workspace_path
                WHERE workspace_id = ? AND root_path = ?
            ''', (workspace_id, root_path.strip()))

            success = cursor.rowcount > 0
            conn.commit()

            return success

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def remove_by_id(cls, path_id: int) -> bool:
        """
        Remove a workspace path by its ID.

        Args:
            path_id: The workspace path ID

        Returns:
            bool: True if path was removed, False if not found
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM workspace_path WHERE id = ?', (path_id,))

            success = cursor.rowcount > 0
            conn.commit()

            return success

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def get_paths_for_workspace(cls, workspace_id: int) -> List['WorkspacePath']:
        """
        Get all paths for a workspace.

        Args:
            workspace_id: The workspace ID

        Returns:
            List[WorkspacePath]: List of paths for the workspace
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, workspace_id, root_path, type
                FROM workspace_path
                WHERE workspace_id = ?
                ORDER BY type ASC, root_path ASC
            ''', (workspace_id,))

            paths = []
            for row in cursor.fetchall():
                path = cls(
                    id=row['id'],
                    workspace_id=row['workspace_id'],
                    root_path=row['root_path'],
                    path_type=row['type']
                )
                paths.append(path)

            return paths

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, path_id: int) -> Optional['WorkspacePath']:
        """
        Get a workspace path by its ID.

        Args:
            path_id: The workspace path ID

        Returns:
            WorkspacePath: The workspace path if found, None otherwise
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, workspace_id, root_path, type
                FROM workspace_path
                WHERE id = ?
            ''', (path_id,))

            row = cursor.fetchone()
            if row:
                return cls(
                    id=row['id'],
                    workspace_id=row['workspace_id'],
                    root_path=row['root_path'],
                    path_type=row['type']
                )
            return None

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def path_exists(cls, workspace_id: int, root_path: str) -> bool:
        """
        Check if a path already exists for a workspace.

        Args:
            workspace_id: The workspace ID
            root_path: The path to check

        Returns:
            bool: True if path exists, False otherwise
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id FROM workspace_path
                WHERE workspace_id = ? AND root_path = ?
            ''', (workspace_id, root_path.strip()))

            return cursor.fetchone() is not None

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert workspace path to dictionary representation.

        Returns:
            dict: Dictionary with workspace path data
        """
        return {
            'id': self.id,
            'workspace_id': self.workspace_id,
            'root_path': self.root_path,
            'type': self.path_type
        }

    def __str__(self) -> str:
        return f"WorkspacePath(id={self.id}, workspace_id={self.workspace_id}, root_path='{self.root_path}', type='{self.path_type}')"

    def __repr__(self) -> str:
        return self.__str__()


class Tag:
    """Model for tag data and operations."""

    def __init__(self, id: Optional[int] = None, file_id: int = 0, tag_name: str = ""):
        self.id = id
        self.file_id = file_id
        self.tag_name = tag_name

    @classmethod
    def add_tag_to_file(cls, file_id: int, tag_name: str) -> 'Tag':
        """
        Add a tag to a file.

        Args:
            file_id: The file entry ID
            tag_name: The tag name to add

        Returns:
            Tag: The created tag

        Raises:
            ValueError: If file_id doesn't exist or tag_name is empty
            sqlite3.IntegrityError: If tag already exists for this file
        """
        # Validate tag_name is not empty
        if not tag_name or not tag_name.strip():
            raise ValueError("tag_name cannot be empty")

        tag_name = tag_name.strip()

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Verify file exists
            cursor.execute('SELECT id FROM file_entry WHERE id = ?', (file_id,))
            if not cursor.fetchone():
                raise ValueError(f"File with ID {file_id} does not exist")

            # Insert the tag
            cursor.execute('''
                INSERT INTO tags (file_id, tag_name)
                VALUES (?, ?)
            ''', (file_id, tag_name))

            tag_id = cursor.lastrowid
            conn.commit()

            return cls(id=tag_id, file_id=file_id, tag_name=tag_name)

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def remove_tag_from_file(cls, file_id: int, tag_name: str) -> bool:
        """
        Remove a tag from a file.

        Args:
            file_id: The file entry ID
            tag_name: The tag name to remove

        Returns:
            bool: True if tag was removed, False if not found
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                DELETE FROM tags
                WHERE file_id = ? AND tag_name = ?
            ''', (file_id, tag_name.strip()))

            success = cursor.rowcount > 0
            conn.commit()

            return success

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def remove_tag_by_id(cls, tag_id: int) -> bool:
        """
        Remove a tag by its ID.

        Args:
            tag_id: The tag ID

        Returns:
            bool: True if tag was removed, False if not found
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))

            success = cursor.rowcount > 0
            conn.commit()

            return success

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def get_tags_for_file(cls, file_id: int) -> List['Tag']:
        """
        Get all tags for a specific file.

        Args:
            file_id: The file entry ID

        Returns:
            List[Tag]: List of tags for the file, ordered by tag_name
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, file_id, tag_name
                FROM tags
                WHERE file_id = ?
                ORDER BY tag_name ASC
            ''', (file_id,))

            tags = []
            for row in cursor.fetchall():
                tag = cls(
                    id=row['id'],
                    file_id=row['file_id'],
                    tag_name=row['tag_name']
                )
                tags.append(tag)

            return tags

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def get_all_unique_tags(cls) -> List[str]:
        """
        Get all unique tag names in the database.

        Returns:
            List[str]: List of unique tag names, ordered alphabetically
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT DISTINCT tag_name
                FROM tags
                ORDER BY tag_name ASC
            ''')

            tags = [row['tag_name'] for row in cursor.fetchall()]
            return tags

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def get_by_id(cls, tag_id: int) -> Optional['Tag']:
        """
        Get a tag by its ID.

        Args:
            tag_id: The tag ID

        Returns:
            Tag: The tag if found, None otherwise
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, file_id, tag_name
                FROM tags
                WHERE id = ?
            ''', (tag_id,))

            row = cursor.fetchone()
            if row:
                return cls(
                    id=row['id'],
                    file_id=row['file_id'],
                    tag_name=row['tag_name']
                )
            return None

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def tag_exists_for_file(cls, file_id: int, tag_name: str) -> bool:
        """
        Check if a tag already exists for a file.

        Args:
            file_id: The file entry ID
            tag_name: The tag name to check

        Returns:
            bool: True if tag exists for the file, False otherwise
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id FROM tags
                WHERE file_id = ? AND tag_name = ?
            ''', (file_id, tag_name.strip()))

            return cursor.fetchone() is not None

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert tag to dictionary representation.

        Returns:
            dict: Dictionary with tag data
        """
        return {
            'id': self.id,
            'file_id': self.file_id,
            'tag_name': self.tag_name
        }

    def __str__(self) -> str:
        return f"Tag(id={self.id}, file_id={self.file_id}, tag_name='{self.tag_name}')"

    def __repr__(self) -> str:
        return self.__str__()