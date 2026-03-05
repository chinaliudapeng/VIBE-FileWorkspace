"""
Data models and CRUD operations for Workspace File Indexer.

This module provides the core data layer for managing workspaces, workspace paths,
file entries, and tags. All database operations should go through this module
to maintain a single source of truth.
"""

import sqlite3
import re
import os
import platform
from datetime import datetime
from pathlib import Path, PurePath
from typing import List, Dict, Optional, Any
from .db import get_connection
from .logging_config import get_logger

logger = get_logger('models')


def validate_regex_patterns(hiding_rules: str) -> None:
    """
    Validate semicolon-separated regex patterns.

    Args:
        hiding_rules: Semicolon-separated regex patterns

    Raises:
        ValueError: If any regex pattern is invalid
    """
    if not hiding_rules or not hiding_rules.strip():
        return

    rules = [rule.strip() for rule in hiding_rules.split(';') if rule.strip()]
    invalid_patterns = []

    for rule in rules:
        try:
            re.compile(rule)
        except re.error as e:
            invalid_patterns.append(f"'{rule}': {str(e)}")

    if invalid_patterns:
        error_msg = "Invalid regex patterns: " + "; ".join(invalid_patterns)
        raise ValueError(error_msg)


def validate_workspace_path(root_path: str, path_type: str, check_existence: bool = True) -> str:
    """
    Validate and normalize a workspace path for security.

    This function addresses multiple security concerns:
    - Path traversal attacks (.. sequences)
    - Symlink escape attacks
    - Invalid filesystem characters
    - Path length limits
    - Drive letter validation on Windows

    Args:
        root_path: The path to validate
        path_type: Either 'file' or 'folder'
        check_existence: Whether to verify the path exists on filesystem (default True)
                        Set to False for testing with mock paths

    Returns:
        str: The normalized, secure absolute path (or original path for tests)

    Raises:
        ValueError: If the path is invalid or poses security risks
        PermissionError: If the path cannot be accessed due to permissions
    """
    if root_path is None:
        raise ValueError("Path cannot be None")

    if not root_path or not root_path.strip():
        raise ValueError("Path cannot be empty")

    # Check for trailing dots or spaces in path components BEFORE any trimming (Windows issue)
    # This validation must happen for both test mode and production mode
    if platform.system() == "Windows":
        # Normalize separators but don't trim whitespace yet
        normalized_path = root_path.replace('\\', '/')

        # Check if this looks like a problematic component ending
        # We're looking for cases like "/path/file." or "/path/file "
        # But NOT overall whitespace like "  /path/file  "

        # Split by path separator and check each non-empty component
        path_parts = normalized_path.split('/')

        for part in path_parts:
            # Skip empty parts from leading/trailing separators or overall whitespace
            if not part or part.isspace():
                continue
            # Skip legitimate navigation components
            if part in ('.', '..'):
                continue
            # Check for problematic endings in actual path components
            if part.endswith('.') or part.endswith(' '):
                raise ValueError("Path component cannot end with dot or space")

    # Strip leading/trailing whitespace from the entire path for further processing
    root_path = root_path.strip()

    # Detect path traversal attacks before normalization
    if '..' in root_path:
        # Check if this is a legitimate relative path or a potential traversal attack
        path_parts = root_path.replace('\\', '/').split('/')
        if any(part == '..' for part in path_parts):
            raise ValueError("Invalid path format")

    # For testing with mock paths, do minimal validation but preserve original format
    if not check_existence:
        # Basic validation for empty path (already checked above, but for safety)
        if not root_path:
            raise ValueError("Path cannot be empty")

        # Basic character validation - only check for null bytes which are never valid
        if '\x00' in root_path:
            raise ValueError("Path contains null bytes")

        # Return the original path without normalization for tests
        logger.info(f"Path validation successful (test mode): {root_path}")
        return root_path

    # Full validation and normalization for production use
    # Convert to Path object for proper handling
    try:
        path_obj = Path(root_path).resolve()
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid path format: {root_path}. Error: {str(e)}")

    # Get the normalized absolute path string
    normalized_path = str(path_obj)

    # Validate path length (Windows has 260 char limit, Unix typically 4096)
    max_length = 260 if platform.system() == "Windows" else 4096
    if len(normalized_path) > max_length:
        raise ValueError(f"Path too long ({len(normalized_path)} chars, max {max_length})")

    # Check for invalid characters based on platform
    if platform.system() == "Windows":
        invalid_chars = set('<>"|?*')  # Removed colon since it's valid in drive letters
        # Check for reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }

        # Check each path component (skip drive letter for Windows)
        for i, part in enumerate(path_obj.parts):
            # Skip Windows drive letter (first part like "C:\")
            if i == 0 and len(part) >= 2 and part[1] == ':':
                continue

            # Check for invalid characters (except colon in drive letters)
            if any(char in invalid_chars for char in part):
                raise ValueError("Path contains invalid characters")

            # Check for colon in non-drive positions
            if ':' in part:
                raise ValueError("Path contains invalid characters")

            # Check for reserved names (case-insensitive, check base name without extension)
            base_name = part.split('.')[0].upper() if '.' in part else part.upper()
            if base_name in reserved_names:
                raise ValueError(f"Path contains reserved name: {part}")


    # Validate the path exists and is accessible (if check_existence is True)
    if check_existence:
        try:
            if path_type == 'file':
                if not path_obj.exists():
                    raise ValueError("File does not exist")
                try:
                    if not path_obj.is_file():
                        raise ValueError("Path is not a file")
                except FileNotFoundError:
                    # Handle race condition where file disappeared between exists() and is_file() checks
                    raise ValueError("Cannot access path")
            elif path_type == 'folder':
                if not path_obj.exists():
                    raise ValueError("Directory does not exist")
                try:
                    if not path_obj.is_dir():
                        raise ValueError("Path is not a directory")
                except FileNotFoundError:
                    # Handle race condition where directory disappeared between exists() and is_dir() checks
                    raise ValueError("Cannot access path")

            # Test read access
            if path_type == 'file':
                # Try to read file info
                try:
                    path_obj.stat()
                except PermissionError:
                    raise PermissionError(f"No read access to file: {normalized_path}")
            else:  # folder
                # Try to list directory contents
                try:
                    list(path_obj.iterdir())
                except PermissionError:
                    raise PermissionError(f"No read access to directory: {normalized_path}")

        except (OSError, PermissionError, FileNotFoundError) as e:
            if isinstance(e, PermissionError):
                raise
            raise ValueError(f"Cannot access path: {normalized_path}. Error: {str(e)}")

        # Check for symlinks and resolve them securely (only if path exists)
        if path_obj.is_symlink():
            logger.warning(f"Path is a symlink: {normalized_path}")
            try:
                # Already resolved above, but log for security audit
                real_path = path_obj.resolve()
                logger.info(f"Symlink {normalized_path} resolves to {real_path}")
            except (OSError, RuntimeError) as e:
                raise ValueError(f"Cannot resolve symlink: {normalized_path}. Error: {str(e)}")

    logger.info(f"Path validation successful: {normalized_path}")
    return normalized_path


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
            logger.error(f"Attempted to create workspace with empty name: '{name}'")
            raise ValueError("Workspace name cannot be empty")

        logger.debug(f"Creating new workspace: '{name.strip()}'")

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

            logger.info(f"Successfully created workspace '{name.strip()}' with ID {workspace_id}")
            return cls(id=workspace_id, name=name.strip(), created_at=created_at)

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error creating workspace '{name.strip()}': {e}")
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
        logger.info(f"Attempting to delete workspace with ID {workspace_id}")

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Check if workspace exists first
            cursor.execute('SELECT id FROM workspace WHERE id = ?', (workspace_id,))
            if not cursor.fetchone():
                logger.warning(f"Workspace with ID {workspace_id} not found for deletion")
                return False

            # Stop filesystem watcher for this workspace before deletion
            try:
                from . import watcher
                logger.debug(f"Stopping filesystem watcher for workspace {workspace_id}")
                watcher.stop_watching_workspace(workspace_id)
            except Exception as e:
                # Don't fail the delete if watcher cleanup fails
                logger.warning(f"Failed to stop filesystem watcher for workspace {workspace_id}: {e}")
                pass

            # Delete the workspace (cascades to related tables)
            cursor.execute('DELETE FROM workspace WHERE id = ?', (workspace_id,))
            conn.commit()

            logger.info(f"Successfully deleted workspace with ID {workspace_id} and all associated data")
            return True

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error deleting workspace {workspace_id}: {e}")
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

        except sqlite3.IntegrityError as e:
            conn.rollback()
            if "unique" in str(e).lower():
                raise sqlite3.IntegrityError(f"A workspace with the name '{new_name}' already exists")
            raise
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
                 root_path: str = "", path_type: str = "folder", hiding_rules: str = ""):
        self.id = id
        self.workspace_id = workspace_id
        self.root_path = root_path
        self.path_type = path_type  # 'folder' or 'file'
        self.hiding_rules = hiding_rules  # semicolon-separated regex patterns

    @classmethod
    def add_path(cls, workspace_id: int, root_path: str, path_type: str, hiding_rules: str = "", check_existence: bool = True) -> 'WorkspacePath':
        """
        Add a path to a workspace.

        Args:
            workspace_id: The workspace ID
            root_path: The absolute path to the folder or file
            path_type: 'folder' or 'file'
            hiding_rules: Semicolon-separated regex patterns for hiding files (optional)
            check_existence: Whether to verify the path exists on filesystem (default True)
                           Set to False for testing with mock paths

        Returns:
            WorkspacePath: The created workspace path

        Raises:
            ValueError: If workspace_id doesn't exist or path_type is invalid
            sqlite3.IntegrityError: If path already exists for this workspace
        """
        # Validate path_type
        if path_type not in ('folder', 'file'):
            raise ValueError("path_type must be 'folder' or 'file'")

        # Validate and normalize the path securely
        root_path = validate_workspace_path(root_path, path_type, check_existence)

        # Validate hiding rules regex patterns
        validate_regex_patterns(hiding_rules)

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Verify workspace exists
            cursor.execute('SELECT id FROM workspace WHERE id = ?', (workspace_id,))
            if not cursor.fetchone():
                raise ValueError(f"Workspace with ID {workspace_id} does not exist")

            # Insert the workspace path
            cursor.execute('''
                INSERT INTO workspace_path (workspace_id, root_path, type, hiding_rules)
                VALUES (?, ?, ?, ?)
            ''', (workspace_id, root_path, path_type, hiding_rules))

            path_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Added workspace path '{root_path}' to workspace {workspace_id}")
            return cls(id=path_id, workspace_id=workspace_id,
                      root_path=root_path, path_type=path_type, hiding_rules=hiding_rules)

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def update_hiding_rules(cls, path_id: int, hiding_rules: str) -> bool:
        """
        Update the hiding rules for a workspace path.

        Args:
            path_id: The workspace path ID
            hiding_rules: Semicolon-separated regex patterns for hiding files

        Returns:
            bool: True if the update was successful, False otherwise

        Raises:
            ValueError: If any regex pattern is invalid
        """
        # Validate hiding rules regex patterns
        validate_regex_patterns(hiding_rules)
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE workspace_path
                SET hiding_rules = ?
                WHERE id = ?
            ''', (hiding_rules, path_id))

            success = cursor.rowcount > 0
            conn.commit()

            if success:
                logger.info(f"Updated hiding rules for workspace path ID {path_id}")
            else:
                logger.warning(f"No workspace path found with ID {path_id}")

            return success

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error updating hiding rules for path ID {path_id}: {e}")
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
                SELECT id, workspace_id, root_path, type, hiding_rules
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
                    path_type=row['type'],
                    hiding_rules=row['hiding_rules'] or ""
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
                SELECT id, workspace_id, root_path, type, hiding_rules
                FROM workspace_path
                WHERE id = ?
            ''', (path_id,))

            row = cursor.fetchone()
            if row:
                return cls(
                    id=row['id'],
                    workspace_id=row['workspace_id'],
                    root_path=row['root_path'],
                    path_type=row['type'],
                    hiding_rules=row['hiding_rules'] or ""
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
            'type': self.path_type,
            'hiding_rules': self.hiding_rules
        }

    def __str__(self) -> str:
        return f"WorkspacePath(id={self.id}, workspace_id={self.workspace_id}, root_path='{self.root_path}', type='{self.path_type}', hiding_rules='{self.hiding_rules}')"

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
            logger.error(f"Attempted to add empty tag to file {file_id}")
            raise ValueError("tag_name cannot be empty")

        tag_name = tag_name.strip()
        logger.debug(f"Adding tag '{tag_name}' to file {file_id}")

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Verify file exists
            cursor.execute('SELECT id FROM file_entry WHERE id = ?', (file_id,))
            if not cursor.fetchone():
                error_msg = f"File with ID {file_id} does not exist"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Insert the tag
            cursor.execute('''
                INSERT INTO tags (file_id, tag_name)
                VALUES (?, ?)
            ''', (file_id, tag_name))

            tag_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Successfully added tag '{tag_name}' to file {file_id} with tag ID {tag_id}")
            return cls(id=tag_id, file_id=file_id, tag_name=tag_name)

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Database error adding tag '{tag_name}' to file {file_id}: {e}")
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
    def get_tags_for_files_bulk(cls, file_ids: List[int]) -> dict[int, List['Tag']]:
        """
        Get all tags for multiple files in a single query.

        This method solves the N+1 query problem by fetching tags for all files
        in one database call instead of individual queries per file.

        Args:
            file_ids: List of file entry IDs

        Returns:
            Dict mapping file_id to List[Tag]: Dictionary where keys are file IDs
            and values are lists of tags for each file, ordered by tag_name
        """
        if not file_ids:
            return {}

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Create placeholders for the IN clause
            placeholders = ','.join(['?' for _ in file_ids])

            cursor.execute(f'''
                SELECT id, file_id, tag_name
                FROM tags
                WHERE file_id IN ({placeholders})
                ORDER BY file_id ASC, tag_name ASC
            ''', file_ids)

            # Group tags by file_id
            tags_by_file = {}
            for row in cursor.fetchall():
                file_id = row['file_id']
                tag = cls(
                    id=row['id'],
                    file_id=row['file_id'],
                    tag_name=row['tag_name']
                )

                if file_id not in tags_by_file:
                    tags_by_file[file_id] = []
                tags_by_file[file_id].append(tag)

            # Ensure all requested file_ids are in the result (even if they have no tags)
            for file_id in file_ids:
                if file_id not in tags_by_file:
                    tags_by_file[file_id] = []

            return tags_by_file

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