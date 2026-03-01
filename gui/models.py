"""GUI models for the Workspace File Indexer application."""

from typing import List, Optional, Any
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QFont

# Import core data models
from core.scanner import FileEntry


class FileTableModel(QAbstractTableModel):
    """Table model for displaying FileEntry data in a QTableView."""

    # Column indices
    COL_RELATIVE_PATH = 0
    COL_FILE_TYPE = 1
    COL_ABSOLUTE_PATH = 2
    COL_TAGS = 3  # Will be implemented in Phase 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._files: List[FileEntry] = []
        self._workspace_id: Optional[int] = None
        self._headers = ["Relative Path", "File Type", "Absolute Path", "Tags"]

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
            if column == self.COL_RELATIVE_PATH:
                return file_entry.relative_path
            elif column == self.COL_FILE_TYPE:
                return file_entry.file_type
            elif column == self.COL_ABSOLUTE_PATH:
                return file_entry.absolute_path
            elif column == self.COL_TAGS:
                # TODO: Implement in Phase 8 - get tags for this file
                return "Tags coming in Phase 8"

        elif role == Qt.ToolTipRole:
            # Show full absolute path as tooltip for all columns
            return file_entry.absolute_path

        elif role == Qt.FontRole:
            # Use monospace font for paths for better readability
            if column in (self.COL_RELATIVE_PATH, self.COL_ABSOLUTE_PATH):
                font = QFont("Consolas", 10)
                font.setFamilies(["Consolas", "Monaco", "Courier New", "monospace"])
                return font

        elif role == Qt.UserRole:
            # Store the FileEntry object for easy access
            return file_entry

        return None

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

    def load_workspace_files(self, workspace_id: int) -> None:
        """
        Load files for the specified workspace.

        Args:
            workspace_id: The workspace ID to load files for
        """
        try:
            self.beginResetModel()
            self._workspace_id = workspace_id
            self._files = FileEntry.get_files_for_workspace(workspace_id)
            self.endResetModel()
        except Exception as e:
            # Reset to empty state on error
            self.beginResetModel()
            self._workspace_id = None
            self._files = []
            self.endResetModel()
            raise e

    def clear_files(self) -> None:
        """Clear all files from the model."""
        self.beginResetModel()
        self._workspace_id = None
        self._files = []
        self.endResetModel()

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