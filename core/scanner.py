"""
Filesystem scanner for Workspace File Indexer.

This module provides functionality to scan workspace paths and populate the
file_entry database table with discovered files.
"""

import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from .db import get_connection
from .models import WorkspacePath


class FileEntry:
    """Model for file entry data."""

    def __init__(self, id: Optional[int] = None, workspace_id: int = 0,
                 relative_path: str = "", absolute_path: str = "", file_type: str = ""):
        self.id = id
        self.workspace_id = workspace_id
        self.relative_path = relative_path
        self.absolute_path = absolute_path
        self.file_type = file_type

    @classmethod
    def create(cls, workspace_id: int, relative_path: str, absolute_path: str, file_type: str = "") -> 'FileEntry':
        """
        Create a new file entry in the database.

        Args:
            workspace_id: The workspace ID
            relative_path: Path relative to the workspace root
            absolute_path: Full absolute path to the file
            file_type: File type/extension

        Returns:
            FileEntry: The created file entry with ID populated

        Raises:
            sqlite3.IntegrityError: If absolute_path already exists
            ValueError: If workspace_id doesn't exist
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Verify workspace exists
            cursor.execute('SELECT id FROM workspace WHERE id = ?', (workspace_id,))
            if not cursor.fetchone():
                raise ValueError(f"Workspace with ID {workspace_id} does not exist")

            cursor.execute('''
                INSERT INTO file_entry (workspace_id, relative_path, absolute_path, file_type)
                VALUES (?, ?, ?, ?)
            ''', (workspace_id, relative_path, absolute_path, file_type))

            file_id = cursor.lastrowid
            conn.commit()

            return cls(id=file_id, workspace_id=workspace_id,
                      relative_path=relative_path, absolute_path=absolute_path, file_type=file_type)

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def get_files_for_workspace(cls, workspace_id: int) -> List['FileEntry']:
        """
        Get all file entries for a workspace.

        Args:
            workspace_id: The workspace ID

        Returns:
            List[FileEntry]: List of file entries for the workspace
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, workspace_id, relative_path, absolute_path, file_type
                FROM file_entry
                WHERE workspace_id = ?
                ORDER BY relative_path ASC
            ''', (workspace_id,))

            files = []
            for row in cursor.fetchall():
                file_entry = cls(
                    id=row['id'],
                    workspace_id=row['workspace_id'],
                    relative_path=row['relative_path'],
                    absolute_path=row['absolute_path'],
                    file_type=row['file_type']
                )
                files.append(file_entry)

            return files

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def delete_by_absolute_path(cls, absolute_path: str) -> bool:
        """
        Delete a file entry by its absolute path.

        Args:
            absolute_path: The absolute path to delete

        Returns:
            bool: True if file was deleted, False if not found
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM file_entry WHERE absolute_path = ?', (absolute_path,))
            success = cursor.rowcount > 0
            conn.commit()

            return success

        except sqlite3.Error as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    @classmethod
    def get_by_absolute_path(cls, absolute_path: str) -> Optional['FileEntry']:
        """
        Get a file entry by its absolute path.

        Args:
            absolute_path: The absolute path

        Returns:
            FileEntry: The file entry if found, None otherwise
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT id, workspace_id, relative_path, absolute_path, file_type
                FROM file_entry
                WHERE absolute_path = ?
            ''', (absolute_path,))

            row = cursor.fetchone()
            if row:
                return cls(
                    id=row['id'],
                    workspace_id=row['workspace_id'],
                    relative_path=row['relative_path'],
                    absolute_path=row['absolute_path'],
                    file_type=row['file_type']
                )
            return None

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert file entry to dictionary representation.

        Returns:
            dict: Dictionary with file entry data
        """
        return {
            'id': self.id,
            'workspace_id': self.workspace_id,
            'relative_path': self.relative_path,
            'absolute_path': self.absolute_path,
            'file_type': self.file_type
        }

    def __str__(self) -> str:
        return f"FileEntry(id={self.id}, workspace_id={self.workspace_id}, relative_path='{self.relative_path}', file_type='{self.file_type}')"

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def search_by_keyword(cls, keyword: str, workspace_id: Optional[int] = None) -> List['FileEntry']:
        """
        Search for files by keyword in file path.

        Args:
            keyword: The keyword to search for in file paths
            workspace_id: Optional workspace ID to limit search to

        Returns:
            List[FileEntry]: List of matching file entries
        """
        conn = get_connection()
        try:
            cursor = conn.cursor()

            if workspace_id:
                cursor.execute('''
                    SELECT id, workspace_id, relative_path, absolute_path, file_type
                    FROM file_entry
                    WHERE workspace_id = ? AND (relative_path LIKE ? OR absolute_path LIKE ?)
                    ORDER BY relative_path ASC
                ''', (workspace_id, f'%{keyword}%', f'%{keyword}%'))
            else:
                cursor.execute('''
                    SELECT id, workspace_id, relative_path, absolute_path, file_type
                    FROM file_entry
                    WHERE relative_path LIKE ? OR absolute_path LIKE ?
                    ORDER BY relative_path ASC
                ''', (f'%{keyword}%', f'%{keyword}%'))

            files = []
            for row in cursor.fetchall():
                file_entry = cls(
                    id=row['id'],
                    workspace_id=row['workspace_id'],
                    relative_path=row['relative_path'],
                    absolute_path=row['absolute_path'],
                    file_type=row['file_type']
                )
                files.append(file_entry)

            return files

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def search_by_tags(cls, tag_names: List[str], workspace_id: Optional[int] = None) -> List['FileEntry']:
        """
        Search for files by tag names.

        Args:
            tag_names: List of tag names to search for
            workspace_id: Optional workspace ID to limit search to

        Returns:
            List[FileEntry]: List of matching file entries
        """
        if not tag_names:
            return []

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Create placeholders for the IN clause
            placeholders = ','.join(['?' for _ in tag_names])

            if workspace_id:
                query = f'''
                    SELECT DISTINCT fe.id, fe.workspace_id, fe.relative_path, fe.absolute_path, fe.file_type
                    FROM file_entry fe
                    INNER JOIN tags t ON fe.id = t.file_id
                    WHERE fe.workspace_id = ? AND t.tag_name IN ({placeholders})
                    ORDER BY fe.relative_path ASC
                '''
                params = [workspace_id] + tag_names
            else:
                query = f'''
                    SELECT DISTINCT fe.id, fe.workspace_id, fe.relative_path, fe.absolute_path, fe.file_type
                    FROM file_entry fe
                    INNER JOIN tags t ON fe.id = t.file_id
                    WHERE t.tag_name IN ({placeholders})
                    ORDER BY fe.relative_path ASC
                '''
                params = tag_names

            cursor.execute(query, params)

            files = []
            for row in cursor.fetchall():
                file_entry = cls(
                    id=row['id'],
                    workspace_id=row['workspace_id'],
                    relative_path=row['relative_path'],
                    absolute_path=row['absolute_path'],
                    file_type=row['file_type']
                )
                files.append(file_entry)

            return files

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()

    @classmethod
    def search_by_keyword_and_tags(cls, keyword: str, tag_names: List[str], workspace_id: Optional[int] = None) -> List['FileEntry']:
        """
        Search for files by both keyword and tags.

        Args:
            keyword: The keyword to search for in file paths
            tag_names: List of tag names to search for
            workspace_id: Optional workspace ID to limit search to

        Returns:
            List[FileEntry]: List of matching file entries (files that match both criteria)
        """
        if not tag_names:
            return cls.search_by_keyword(keyword, workspace_id)

        conn = get_connection()
        try:
            cursor = conn.cursor()

            # Create placeholders for the IN clause
            placeholders = ','.join(['?' for _ in tag_names])

            if workspace_id:
                query = f'''
                    SELECT DISTINCT fe.id, fe.workspace_id, fe.relative_path, fe.absolute_path, fe.file_type
                    FROM file_entry fe
                    INNER JOIN tags t ON fe.id = t.file_id
                    WHERE fe.workspace_id = ?
                    AND (fe.relative_path LIKE ? OR fe.absolute_path LIKE ?)
                    AND t.tag_name IN ({placeholders})
                    ORDER BY fe.relative_path ASC
                '''
                params = [workspace_id, f'%{keyword}%', f'%{keyword}%'] + tag_names
            else:
                query = f'''
                    SELECT DISTINCT fe.id, fe.workspace_id, fe.relative_path, fe.absolute_path, fe.file_type
                    FROM file_entry fe
                    INNER JOIN tags t ON fe.id = t.file_id
                    WHERE (fe.relative_path LIKE ? OR fe.absolute_path LIKE ?)
                    AND t.tag_name IN ({placeholders})
                    ORDER BY fe.relative_path ASC
                '''
                params = [f'%{keyword}%', f'%{keyword}%'] + tag_names

            cursor.execute(query, params)

            files = []
            for row in cursor.fetchall():
                file_entry = cls(
                    id=row['id'],
                    workspace_id=row['workspace_id'],
                    relative_path=row['relative_path'],
                    absolute_path=row['absolute_path'],
                    file_type=row['file_type']
                )
                files.append(file_entry)

            return files

        except sqlite3.Error as e:
            raise
        finally:
            conn.close()


class FilesystemScanner:
    """Scanner for discovering files in workspace paths."""

    def __init__(self, workspace_id: int):
        """
        Initialize the scanner for a specific workspace.

        Args:
            workspace_id: The workspace ID to scan files for
        """
        self.workspace_id = workspace_id

    def _get_file_type(self, file_path: Path) -> str:
        """
        Determine the file type based on the file extension.

        Args:
            file_path: Path to the file

        Returns:
            str: File type (extension without dot, or 'unknown')
        """
        suffix = file_path.suffix.lower()
        if suffix:
            return suffix[1:]  # Remove the dot
        return 'unknown'

    def _scan_directory(self, directory_path: Path, root_path: Path) -> List[Dict[str, str]]:
        """
        Recursively scan a directory for files.

        Args:
            directory_path: Directory to scan
            root_path: Root path for calculating relative paths

        Returns:
            List[Dict]: List of file info dictionaries
        """
        discovered_files = []

        try:
            for item in directory_path.rglob('*'):
                if item.is_file():
                    try:
                        # Calculate relative path from the root
                        relative_path = item.relative_to(root_path)
                        absolute_path = str(item.resolve())
                        file_type = self._get_file_type(item)

                        discovered_files.append({
                            'relative_path': str(relative_path),
                            'absolute_path': absolute_path,
                            'file_type': file_type
                        })
                    except (OSError, ValueError) as e:
                        # Skip files we can't access or process
                        print(f"Warning: Could not process file {item}: {e}")
                        continue

        except (OSError, PermissionError) as e:
            print(f"Warning: Could not access directory {directory_path}: {e}")

        return discovered_files

    def _scan_single_file(self, file_path: Path, root_path: Path) -> List[Dict[str, str]]:
        """
        Scan a single file.

        Args:
            file_path: File to scan
            root_path: Root path for calculating relative paths

        Returns:
            List[Dict]: List containing single file info dictionary
        """
        discovered_files = []

        try:
            if file_path.exists() and file_path.is_file():
                # For single files, the relative path is just the filename
                relative_path = file_path.name
                absolute_path = str(file_path.resolve())
                file_type = self._get_file_type(file_path)

                discovered_files.append({
                    'relative_path': relative_path,
                    'absolute_path': absolute_path,
                    'file_type': file_type
                })
        except (OSError, ValueError) as e:
            print(f"Warning: Could not process file {file_path}: {e}")

        return discovered_files

    def scan_workspace_paths(self) -> int:
        """
        Scan all paths associated with the workspace and populate the database.

        Returns:
            int: Number of files discovered and added to the database

        Raises:
            ValueError: If workspace doesn't exist
        """
        # Get all workspace paths
        workspace_paths = WorkspacePath.get_paths_for_workspace(self.workspace_id)

        if not workspace_paths:
            print(f"No paths found for workspace ID {self.workspace_id}")
            return 0

        total_files_added = 0

        for workspace_path in workspace_paths:
            path_obj = Path(workspace_path.root_path)

            if not path_obj.exists():
                print(f"Warning: Path does not exist: {workspace_path.root_path}")
                continue

            print(f"Scanning {workspace_path.path_type}: {workspace_path.root_path}")

            discovered_files = []

            if workspace_path.path_type == 'folder' and path_obj.is_dir():
                discovered_files = self._scan_directory(path_obj, path_obj)
            elif workspace_path.path_type == 'file' and path_obj.is_file():
                discovered_files = self._scan_single_file(path_obj, path_obj.parent)

            # Add discovered files to the database
            for file_info in discovered_files:
                try:
                    FileEntry.create(
                        workspace_id=self.workspace_id,
                        relative_path=file_info['relative_path'],
                        absolute_path=file_info['absolute_path'],
                        file_type=file_info['file_type']
                    )
                    total_files_added += 1
                except sqlite3.IntegrityError:
                    # File already exists in database, skip
                    print(f"File already indexed: {file_info['absolute_path']}")
                    continue
                except Exception as e:
                    print(f"Error adding file to database: {file_info['absolute_path']}: {e}")
                    continue

        print(f"Scanning complete. Added {total_files_added} files to the database.")
        return total_files_added

    def rescan_workspace(self) -> Dict[str, int]:
        """
        Rescan the workspace, removing stale entries and adding new ones.

        Returns:
            Dict[str, int]: Statistics about the rescan (removed, added, total)
        """
        # Get current file entries for this workspace
        current_files = FileEntry.get_files_for_workspace(self.workspace_id)
        current_absolute_paths = {f.absolute_path for f in current_files}

        # Scan for current files
        self.scan_workspace_paths()

        # Get updated file list after scanning
        updated_files = FileEntry.get_files_for_workspace(self.workspace_id)
        updated_absolute_paths = {f.absolute_path for f in updated_files}

        # Remove files that no longer exist
        removed_count = 0
        for file_entry in current_files:
            file_path = Path(file_entry.absolute_path)
            if not file_path.exists():
                FileEntry.delete_by_absolute_path(file_entry.absolute_path)
                removed_count += 1

        # Count newly added files
        newly_added = updated_absolute_paths - current_absolute_paths
        added_count = len(newly_added)

        final_files = FileEntry.get_files_for_workspace(self.workspace_id)
        total_count = len(final_files)

        return {
            'removed': removed_count,
            'added': added_count,
            'total': total_count
        }


def scan_workspace(workspace_id: int) -> int:
    """
    Convenience function to scan a workspace by ID.

    Args:
        workspace_id: The workspace ID to scan

    Returns:
        int: Number of files discovered and added

    Raises:
        ValueError: If workspace doesn't exist
    """
    scanner = FilesystemScanner(workspace_id)
    return scanner.scan_workspace_paths()


def rescan_workspace(workspace_id: int) -> Dict[str, int]:
    """
    Convenience function to rescan a workspace by ID.

    Args:
        workspace_id: The workspace ID to rescan

    Returns:
        Dict[str, int]: Rescan statistics
    """
    scanner = FilesystemScanner(workspace_id)
    return scanner.rescan_workspace()