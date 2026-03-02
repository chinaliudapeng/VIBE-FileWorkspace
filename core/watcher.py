"""
Filesystem watcher for Workspace File Indexer.

This module provides real-time filesystem monitoring using the watchdog library
to detect file creations, deletions, and modifications and automatically update
the database accordingly.
"""

import os
import ctypes
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .scanner import FileEntry
from .models import Workspace, WorkspacePath


class WorkspaceFileHandler(FileSystemEventHandler):
    """Handles filesystem events for a specific workspace."""

    def __init__(self, workspace_id: int, watcher: 'FilesystemWatcher'):
        """
        Initialize the file handler for a workspace.

        Args:
            workspace_id: The workspace ID to handle events for
            watcher: Reference to the parent watcher instance
        """
        super().__init__()
        self.workspace_id = workspace_id
        self.watcher = watcher

    def _get_file_type(self, file_path: Path) -> str:
        """
        Determine the file type based on the file extension.

        Args:
            file_path: Path to the file

        Returns:
            str: File type (extension without dot, or 'unknown')
        """
        if file_path.is_dir():
            return 'directory'
        suffix = file_path.suffix.lower()
        if suffix:
            return suffix[1:]  # Remove the dot
        return 'unknown'

    def _is_hidden(self, path: Path) -> bool:
        """Check if a file or directory is hidden."""
        # Check if any part of the path starts with a dot
        if any(part.startswith('.') for part in path.parts):
            return True
            
        # Check Windows hidden attribute
        if os.name == 'nt':
            try:
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
                if attrs != -1 and bool(attrs & 2):  # FILE_ATTRIBUTE_HIDDEN = 2
                    return True
            except Exception:
                pass
                
        return False

    def _calculate_relative_path(self, absolute_path: str) -> Optional[str]:
        """
        Calculate the relative path for a file within the workspace.

        Args:
            absolute_path: The absolute path to the file

        Returns:
            str: Relative path from workspace root, or None if not within workspace
        """
        abs_path = Path(absolute_path).resolve()

        # Get workspace paths to determine which root this file belongs to
        workspace_paths = WorkspacePath.get_paths_for_workspace(self.workspace_id)

        for workspace_path in workspace_paths:
            root_path = Path(workspace_path.root_path).resolve()

            try:
                if workspace_path.path_type == 'folder' and abs_path.is_relative_to(root_path):
                    return str(abs_path.relative_to(root_path))
                elif workspace_path.path_type == 'file' and abs_path == root_path:
                    return abs_path.name
            except (ValueError, OSError):
                continue

        return None

    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        absolute_path = str(Path(event.src_path).resolve())
        file_path = Path(absolute_path)
        
        if self._is_hidden(file_path):
            return

        relative_path = self._calculate_relative_path(absolute_path)

        if relative_path is None:
            return  # File is not within any workspace path

        # For directories, watchdog events might fire before we can check is_dir() sometimes, 
        # but since we rely on event.is_directory we can just hardcode the type
        file_type = 'directory' if event.is_directory else self._get_file_type(file_path)

        try:
            FileEntry.create(
                workspace_id=self.workspace_id,
                relative_path=relative_path,
                absolute_path=absolute_path,
                file_type=file_type
            )
            print(f"Added to index: {relative_path}")
        except sqlite3.IntegrityError:
            # File already exists in database
            pass
        except Exception as e:
            print(f"Error adding to index: {absolute_path}: {e}")

    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        absolute_path = str(Path(event.src_path).resolve())

        try:
            if FileEntry.delete_by_absolute_path(absolute_path):
                print(f"Removed from index: {absolute_path}")
        except Exception as e:
            print(f"Error removing from index: {absolute_path}: {e}")

    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename events."""
        old_absolute_path = str(Path(event.src_path).resolve())
        new_absolute_path = str(Path(event.dest_path).resolve())
        new_file_path = Path(new_absolute_path)
        
        # Remove old entry
        try:
            FileEntry.delete_by_absolute_path(old_absolute_path)
            print(f"Removed old entry: {old_absolute_path}")
        except Exception as e:
            print(f"Error removing old entry: {old_absolute_path}: {e}")

        # If it was moved to a hidden destination, stop here
        if self._is_hidden(new_file_path):
            return

        # Add new entry if still within workspace
        new_relative_path = self._calculate_relative_path(new_absolute_path)
        if new_relative_path is not None:
            file_type = 'directory' if event.is_directory else self._get_file_type(new_file_path)

            try:
                FileEntry.create(
                    workspace_id=self.workspace_id,
                    relative_path=new_relative_path,
                    absolute_path=new_absolute_path,
                    file_type=file_type
                )
                print(f"Added moved entry to index: {new_relative_path}")
            except sqlite3.IntegrityError:
                pass
            except Exception as e:
                print(f"Error adding moved entry to index: {new_absolute_path}: {e}")

    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        pass


class FilesystemWatcher:
    """Real-time filesystem watcher for workspace files."""

    def __init__(self):
        """Initialize the filesystem watcher."""
        self.observer = Observer()
        self.watching_workspaces: Dict[int, Set[str]] = {}
        self.workspace_handlers: Dict[int, WorkspaceFileHandler] = {}
        self.is_running = False
        self._lock = threading.Lock()

    def start_watching_workspace(self, workspace_id: int) -> bool:
        """
        Start watching filesystem events for a specific workspace.

        Args:
            workspace_id: The workspace ID to watch

        Returns:
            bool: True if watching started successfully, False otherwise
        """
        with self._lock:
            if workspace_id in self.watching_workspaces:
                print(f"Already watching workspace {workspace_id}")
                return True

            # Verify workspace exists
            workspace = Workspace.get_by_id(workspace_id)
            if not workspace:
                print(f"Workspace {workspace_id} does not exist")
                return False

            # Get workspace paths
            workspace_paths = WorkspacePath.get_paths_for_workspace(workspace_id)
            if not workspace_paths:
                print(f"No paths found for workspace {workspace_id}")
                return False

            # Create handler for this workspace
            handler = WorkspaceFileHandler(workspace_id, self)
            self.workspace_handlers[workspace_id] = handler

            # Watch each path in the workspace
            watched_paths = set()
            for workspace_path in workspace_paths:
                path_obj = Path(workspace_path.root_path)

                if not path_obj.exists():
                    print(f"Warning: Path does not exist: {workspace_path.root_path}")
                    continue

                try:
                    if workspace_path.path_type == 'folder' and path_obj.is_dir():
                        # Watch the directory recursively
                        self.observer.schedule(handler, str(path_obj), recursive=True)
                        watched_paths.add(str(path_obj))
                        print(f"Watching directory: {path_obj}")
                    elif workspace_path.path_type == 'file' and path_obj.is_file():
                        # Watch the parent directory of the file
                        parent_dir = path_obj.parent
                        if str(parent_dir) not in watched_paths:
                            self.observer.schedule(handler, str(parent_dir), recursive=False)
                            watched_paths.add(str(parent_dir))
                            print(f"Watching file's parent directory: {parent_dir}")
                except Exception as e:
                    print(f"Error watching path {workspace_path.root_path}: {e}")
                    continue

            if watched_paths:
                self.watching_workspaces[workspace_id] = watched_paths

                # Start observer if not already running
                if not self.is_running:
                    self.observer.start()
                    self.is_running = True
                    print("Filesystem watcher started")

                return True
            else:
                print(f"No valid paths to watch for workspace {workspace_id}")
                return False

    def stop_watching_workspace(self, workspace_id: int) -> bool:
        """
        Stop watching filesystem events for a specific workspace.

        Args:
            workspace_id: The workspace ID to stop watching

        Returns:
            bool: True if watching stopped successfully, False if wasn't watching
        """
        with self._lock:
            if workspace_id not in self.watching_workspaces:
                return False

            # Remove the workspace from our tracking
            del self.watching_workspaces[workspace_id]
            if workspace_id in self.workspace_handlers:
                del self.workspace_handlers[workspace_id]

            # If no workspaces are being watched, stop the observer
            if not self.watching_workspaces and self.is_running:
                self.observer.stop()
                self.observer.join(timeout=1.0)  # Give it 1 second to stop gracefully
                self.observer = Observer()  # Create new observer for future use
                self.is_running = False
                print("Filesystem watcher stopped")

            return True

    def start_watching_all_workspaces(self) -> int:
        """
        Start watching all existing workspaces.

        Returns:
            int: Number of workspaces successfully being watched
        """
        workspaces = Workspace.list_all()
        successful_count = 0

        for workspace in workspaces:
            if self.start_watching_workspace(workspace.id):
                successful_count += 1

        return successful_count

    def stop_all_watching(self):
        """Stop watching all workspaces and shutdown the observer."""
        with self._lock:
            if self.is_running:
                self.observer.stop()
                self.observer.join(timeout=1.0)  # Give it 1 second to stop gracefully
                self.observer = Observer()  # Create new observer for future use
                self.is_running = False

            self.watching_workspaces.clear()
            self.workspace_handlers.clear()
            print("All filesystem watching stopped")

    def get_watched_workspaces(self) -> Dict[int, Set[str]]:
        """
        Get the currently watched workspaces and their paths.

        Returns:
            Dict[int, Set[str]]: Mapping of workspace IDs to their watched paths
        """
        return self.watching_workspaces.copy()

    def is_watching_workspace(self, workspace_id: int) -> bool:
        """
        Check if a workspace is currently being watched.

        Args:
            workspace_id: The workspace ID to check

        Returns:
            bool: True if workspace is being watched, False otherwise
        """
        return workspace_id in self.watching_workspaces

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_all_watching()


# Global watcher instance
_global_watcher: Optional[FilesystemWatcher] = None


def get_global_watcher() -> FilesystemWatcher:
    """
    Get the global filesystem watcher instance.

    Returns:
        FilesystemWatcher: The global watcher instance
    """
    global _global_watcher
    if _global_watcher is None:
        _global_watcher = FilesystemWatcher()
    return _global_watcher


def start_watching_workspace(workspace_id: int) -> bool:
    """
    Convenience function to start watching a workspace using the global watcher.

    Args:
        workspace_id: The workspace ID to watch

    Returns:
        bool: True if watching started successfully, False otherwise
    """
    watcher = get_global_watcher()
    return watcher.start_watching_workspace(workspace_id)


def stop_watching_workspace(workspace_id: int) -> bool:
    """
    Convenience function to stop watching a workspace using the global watcher.

    Args:
        workspace_id: The workspace ID to stop watching

    Returns:
        bool: True if watching stopped successfully, False if wasn't watching
    """
    watcher = get_global_watcher()
    return watcher.stop_watching_workspace(workspace_id)


def start_watching_all_workspaces() -> int:
    """
    Convenience function to start watching all workspaces using the global watcher.

    Returns:
        int: Number of workspaces successfully being watched
    """
    watcher = get_global_watcher()
    return watcher.start_watching_all_workspaces()


def stop_all_watching():
    """
    Convenience function to stop all watching using the global watcher.
    """
    watcher = get_global_watcher()
    watcher.stop_all_watching()