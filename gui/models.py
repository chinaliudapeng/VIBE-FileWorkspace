"""GUI models for the Workspace File Indexer application."""

from typing import List, Optional, Any
import hashlib
import re
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QFont, QColor

# Import core data models
from core.scanner import FileEntry
from core.models import Tag, WorkspacePath
from core.logging_config import get_logger

logger = get_logger('models')


class FileTableModel(QAbstractTableModel):
    """Table model for displaying FileEntry data in a QTableView."""

    # Column indices
    COL_CHECKBOX = 0
    COL_RELATIVE_PATH = 1
    COL_FILE_TYPE = 2
    COL_ABSOLUTE_PATH = 3
    COL_TAGS = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: List[FileEntry] = []
        self._workspace_id: Optional[int] = None
        self._headers = ["", "Relative Path", "File Type", "Absolute Path", "Tags"]
        self._sort_column = -1
        self._sort_order = Qt.AscendingOrder
        self._tags_cache: dict[int, List[Tag]] = {}  # Cache tags by file_id
        self._checked_files: set[int] = set()  # Set of checked file IDs

    def _get_file_type_color(self, file_type: str) -> QColor:
        """
        Generate a subtle background color based on file type.

        Args:
            file_type: The file type (extension or 'directory')

        Returns:
            QColor: A subtle background color for the file type
        """
        # Special case for directories - use a consistent blue-gray
        if file_type == 'directory':
            return QColor(45, 55, 70)  # Dark blue-gray for directories

        # For empty or unknown file types
        if not file_type:
            return QColor(50, 50, 50)  # Neutral gray

        # Generate hash from file type to ensure consistent colors
        hash_obj = hashlib.md5(file_type.lower().encode())
        hash_hex = hash_obj.hexdigest()

        # Extract RGB values from hash (using first 6 characters)
        r = int(hash_hex[0:2], 16)
        g = int(hash_hex[2:4], 16)
        b = int(hash_hex[4:6], 16)

        # Darken the colors to work well with dark theme
        # Scale down to 30-60% of original brightness for subtle effect
        r = int(r * 0.4) + 25  # Range: 25-127
        g = int(g * 0.4) + 25  # Range: 25-127
        b = int(b * 0.4) + 25  # Range: 25-127

        return QColor(r, g, b)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of rows (files) in the model."""
        if parent.isValid():
            return 0
        return len(self._files)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns in the model."""
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """Return data for the given index and role."""
        if not index.isValid() or index.row() >= len(self._files):
            return None

        file_entry = self._files[index.row()]
        column = index.column()

        if role == Qt.DisplayRole:
            if column == self.COL_CHECKBOX:
                # Checkbox column - no display text
                return ""
            elif column == self.COL_RELATIVE_PATH:
                # Format relative path - show it normally
                return file_entry.relative_path
            elif column == self.COL_FILE_TYPE:
                # File type
                if file_entry.file_type == 'directory':
                    return "Folder"
                return file_entry.file_type.upper() if file_entry.file_type else 'FILE'
            elif column == self.COL_ABSOLUTE_PATH:
                # Absolute path
                return file_entry.absolute_path
            elif column == self.COL_TAGS:
                # Tags are rendered by the custom delegate, not as text
                # Return empty string for display, delegate handles the rendering
                return ""

        elif role == Qt.CheckStateRole:
            if column == self.COL_CHECKBOX:
                # Return checkbox state for the checkbox column
                return Qt.Checked if file_entry.id in self._checked_files else Qt.Unchecked

        elif role == Qt.ToolTipRole:
            # Show full absolute path as tooltip for all columns
            return file_entry.absolute_path

        elif role == Qt.FontRole:
            # Use monospace font for paths for better readability
            if column in (self.COL_RELATIVE_PATH, self.COL_ABSOLUTE_PATH):
                font = QFont("Consolas", 10)
                font.setFamilies(["Consolas", "Monaco", "Courier New", "monospace"])
                return font

        elif role == Qt.BackgroundRole:
            # Return background color based on file type (but not for checkbox column)
            if column != self.COL_CHECKBOX:
                return self._get_file_type_color(file_entry.file_type)

        elif role == Qt.UserRole:
            # Store the FileEntry object for easy access
            return file_entry

        return None

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """Set data for the given index and role."""
        if not index.isValid() or index.row() >= len(self._files):
            return False

        file_entry = self._files[index.row()]
        column = index.column()

        if role == Qt.CheckStateRole and column == self.COL_CHECKBOX:
            # Toggle checkbox state
            if value == Qt.Checked:
                self._checked_files.add(file_entry.id)
            else:
                self._checked_files.discard(file_entry.id)

            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            return True

        return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return the item flags for the given index."""
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable

        # Make checkbox column checkable
        if index.column() == self.COL_CHECKBOX:
            flags |= Qt.ItemIsUserCheckable

        return flags

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        """Return header data for the given section."""
        if orientation != Qt.Horizontal:
            return None

        if role == Qt.DisplayRole:
            if 0 <= section < len(self._headers):
                return self._headers[section]

        elif role == Qt.FontRole:
            font = QFont()
            font.setBold(True)
            return font

        return None

    def _apply_hiding_rules(self, files: List[FileEntry], workspace_id: int) -> List[FileEntry]:
        """
        Apply hiding rules to filter out files that match regex patterns.

        Args:
            files: List of FileEntry objects to filter
            workspace_id: The workspace ID to get hiding rules for

        Returns:
            List[FileEntry]: Filtered list of files
        """
        try:
            # Get workspace paths with their hiding rules
            workspace_paths = WorkspacePath.get_paths_for_workspace(workspace_id)

            # Collect all hiding rules from all workspace paths
            all_hiding_rules = []
            for workspace_path in workspace_paths:
                if workspace_path.hiding_rules and workspace_path.hiding_rules.strip():
                    rules = [rule.strip() for rule in workspace_path.hiding_rules.split(';') if rule.strip()]
                    all_hiding_rules.extend(rules)

            # If no hiding rules, return all files
            if not all_hiding_rules:
                return files

            # Compile regex patterns (with error handling)
            compiled_patterns = []
            for rule in all_hiding_rules:
                try:
                    compiled_patterns.append(re.compile(rule))
                except re.error as e:
                    # Skip invalid regex patterns but don't fail completely
                    logger.warning(f"Invalid regex pattern '{rule}': {e}")
                    continue

            # If no valid patterns, return all files
            if not compiled_patterns:
                return files

            # Filter files based on relative path matching
            filtered_files = []
            for file_entry in files:
                should_hide = False

                # Check if file matches any hiding rule
                for pattern in compiled_patterns:
                    try:
                        if pattern.search(file_entry.relative_path):
                            should_hide = True
                            break
                    except Exception as e:
                        # Skip pattern if it causes an error
                        logger.warning(f"Error applying pattern to '{file_entry.relative_path}': {e}")
                        continue

                # Only add file if it doesn't match any hiding rule
                if not should_hide:
                    filtered_files.append(file_entry)

            return filtered_files

        except Exception as e:
            # If there's an error with hiding rules, don't hide anything
            logger.warning(f"Error applying hiding rules: {e}")
            return files

    def load_workspace_files(self, workspace_id: int) -> None:
        """
        Load files for the specified workspace with hiding rules applied.
        Also preloads all tags to avoid N+1 query problem.

        Args:
            workspace_id: The workspace ID to load files for
        """
        try:
            self.beginResetModel()
            self._workspace_id = workspace_id

            # Get all files for the workspace
            all_files = FileEntry.get_files_for_workspace(workspace_id)

            # Apply hiding rules to filter files
            self._files = self._apply_hiding_rules(all_files, workspace_id)

            # Preload all tags for the filtered files to avoid N+1 query problem
            self._preload_tags()

            self.endResetModel()
        except Exception as e:
            # Reset to empty state on error
            self.beginResetModel()
            self._workspace_id = None
            self._files = []
            self._tags_cache = {}
            self.endResetModel()
            raise e

    def clear_files(self) -> None:
        """Clear all files from the model."""
        self.beginResetModel()
        self._workspace_id = None
        self._files = []
        self._tags_cache = {}
        self._checked_files = set()
        self.endResetModel()

    def _preload_tags(self) -> None:
        """
        Preload all tags for current files to avoid N+1 query problem.
        This method loads all tags in a single database query and caches them.
        """
        if not self._files:
            self._tags_cache = {}
            return

        try:
            # Extract all file IDs
            file_ids = [file_entry.id for file_entry in self._files]

            # Bulk load tags for all files
            self._tags_cache = Tag.get_tags_for_files_bulk(file_ids)

            logger.debug(f"Preloaded tags for {len(file_ids)} files, found tags for {len([f_id for f_id, tags in self._tags_cache.items() if tags])} files")

        except Exception as e:
            logger.warning(f"Failed to preload tags: {e}")
            self._tags_cache = {}

    def get_cached_tags(self, file_id: int) -> List[Tag]:
        """
        Get cached tags for a specific file.

        Args:
            file_id: The file entry ID

        Returns:
            List[Tag]: List of tags for the file, empty list if no tags or file not found
        """
        return self._tags_cache.get(file_id, [])

    def get_file_at_row(self, row: int) -> Optional[FileEntry]:
        """
        Get the FileEntry object at the specified row.

        Args:
            row: The row index

        Returns:
            FileEntry object or None if invalid row
        """
        if 0 <= row < len(self._files):
            return self._files[row]
        return None

    def get_workspace_id(self) -> Optional[int]:
        """Get the currently loaded workspace ID."""
        return self._workspace_id

    def refresh(self) -> None:
        """Refresh the model data by reloading from the database."""
        if self._workspace_id is not None:
            self.load_workspace_files(self._workspace_id)

    def get_file_count(self) -> int:
        """Get the number of files in the current model."""
        return len(self._files)

    def _set_files(self, files: List[FileEntry]) -> None:
        """
        Set files directly (used for filtered search results).
        Also preloads tags for the new file list.

        Args:
            files: List of FileEntry objects to display
        """
        self.beginResetModel()
        self._files = files
        # Preload tags for the new file list
        self._preload_tags()
        self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        """
        Sort the table data by the specified column.

        Args:
            column: The column index to sort by
            order: Qt.AscendingOrder or Qt.DescendingOrder
        """
        if not self._files or column < 0 or column >= len(self._headers):
            return

        self._sort_column = column
        self._sort_order = order

        self.layoutAboutToBeChanged.emit()

        # Define sort key functions for each column
        if column == self.COL_CHECKBOX:
            # Sort by checkbox state (checked files first)
            def sort_key(file_entry: FileEntry) -> tuple:
                is_checked = file_entry.id in self._checked_files
                return (not is_checked, file_entry.relative_path.lower())

        elif column == self.COL_RELATIVE_PATH:
            # Sort by relative path, directories first
            def sort_key(file_entry: FileEntry) -> tuple:
                is_dir = file_entry.file_type == 'directory'
                return (not is_dir, file_entry.relative_path.lower())

        elif column == self.COL_FILE_TYPE:
            # Sort by file type, directories first, then alphabetically by type
            def sort_key(file_entry: FileEntry) -> tuple:
                if file_entry.file_type == 'directory':
                    return (0, 'directory')
                file_type = file_entry.file_type or 'unknown'
                return (1, file_type.lower())

        elif column == self.COL_ABSOLUTE_PATH:
            # Sort by absolute path, directories first
            def sort_key(file_entry: FileEntry) -> tuple:
                is_dir = file_entry.file_type == 'directory'
                return (not is_dir, file_entry.absolute_path.lower())

        elif column == self.COL_TAGS:
            # Sort by number of tags, then alphabetically by first tag name (using cached tags)
            def sort_key(file_entry: FileEntry) -> tuple:
                try:
                    tags = self.get_cached_tags(file_entry.id)
                    if not tags:
                        return (0, '')  # Files with no tags come first
                    tag_names = [tag.tag_name for tag in tags]
                    tag_names.sort()
                    return (len(tags), tag_names[0].lower())
                except Exception:
                    return (0, '')  # Handle any errors gracefully

        else:
            # Default sort by relative path
            def sort_key(file_entry: FileEntry) -> tuple:
                return (file_entry.relative_path.lower(),)

        # Sort the files
        reverse = (order == Qt.DescendingOrder)
        self._files.sort(key=sort_key, reverse=reverse)

        self.layoutChanged.emit()

    # Batch operations methods
    def get_checked_files(self) -> List[FileEntry]:
        """Get a list of currently checked FileEntry objects."""
        checked_files = []
        for file_entry in self._files:
            if file_entry.id in self._checked_files:
                checked_files.append(file_entry)
        return checked_files

    def get_checked_file_count(self) -> int:
        """Get the number of currently checked files."""
        return len(self._checked_files)

    def check_all_files(self) -> None:
        """Check all files in the current model."""
        if not self._files:
            return

        self.layoutAboutToBeChanged.emit()
        for file_entry in self._files:
            self._checked_files.add(file_entry.id)
        self.layoutChanged.emit()

    def uncheck_all_files(self) -> None:
        """Uncheck all files in the current model."""
        if not self._checked_files:
            return

        self.layoutAboutToBeChanged.emit()
        self._checked_files.clear()
        self.layoutChanged.emit()

    def toggle_all_files(self) -> None:
        """Toggle the check state of all files."""
        if len(self._checked_files) == len(self._files):
            # All checked, uncheck all
            self.uncheck_all_files()
        else:
            # Not all checked, check all
            self.check_all_files()

    def is_file_checked(self, file_entry: FileEntry) -> bool:
        """Check if a specific file is checked."""
        return file_entry.id in self._checked_files