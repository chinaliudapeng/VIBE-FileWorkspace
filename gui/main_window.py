"""Main window for the Workspace File Indexer GUI application."""

import sys
import os
import subprocess
import platform
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QListWidget, QLineEdit, QPushButton, QLabel, QListWidgetItem,
    QMessageBox, QMenu, QDialog, QTableView, QHeaderView
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QIcon, QClipboard
import send2trash

# Import core data models
from core.models import Workspace

# Import dialog windows
from gui.dialogs import WorkspaceDialog

# Import GUI models and delegates
from gui.models import FileTableModel
from gui.delegates import TagPillDelegate


class WorkspaceListWidget(QListWidget):
    """Custom list widget for displaying workspaces with database integration."""

    workspace_selected = Signal(object)  # Emits selected Workspace object
    edit_requested = Signal(object)     # Emits workspace to edit
    delete_requested = Signal(object)   # Emits workspace to delete

    def __init__(self, parent=None):
        super().__init__(parent)
        self.workspaces = []  # Store workspace objects
        self.setObjectName("workspaceList")

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Connect selection change signal
        self.currentItemChanged.connect(self._on_selection_changed)

    def load_workspaces(self):
        """Load workspaces from database and populate the list."""
        try:
            self.clear()
            self.workspaces = Workspace.list_all()

            for workspace in self.workspaces:
                item = QListWidgetItem(workspace.name)
                item.setData(Qt.UserRole, workspace)  # Store workspace object
                self.addItem(item)

            # Auto-select first workspace if any exist
            if self.workspaces:
                self.setCurrentRow(0)

        except Exception as e:
            QMessageBox.warning(self, "Database Error",
                              f"Failed to load workspaces: {str(e)}")

    def refresh(self):
        """Refresh the workspace list from database."""
        current_selection = self.get_selected_workspace()
        current_name = current_selection.name if current_selection else None

        self.load_workspaces()

        # Try to restore selection
        if current_name:
            for i in range(self.count()):
                item = self.item(i)
                workspace = item.data(Qt.UserRole)
                if workspace and workspace.name == current_name:
                    self.setCurrentRow(i)
                    break

    def get_selected_workspace(self) -> Optional[Workspace]:
        """Get the currently selected workspace object."""
        current_item = self.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None

    def _on_selection_changed(self, current, previous):
        """Handle workspace selection change."""
        if current:
            workspace = current.data(Qt.UserRole)
            if workspace:
                self.workspace_selected.emit(workspace)

    def _show_context_menu(self, position):
        """Show context menu for workspace items."""
        item = self.itemAt(position)
        if item:
            workspace = item.data(Qt.UserRole)
            if workspace:
                menu = QMenu(self)

                # Edit workspace action
                edit_action = menu.addAction("Edit Workspace")
                edit_action.triggered.connect(lambda: self.edit_requested.emit(workspace))

                # Delete workspace action
                delete_action = menu.addAction("Delete Workspace")
                delete_action.triggered.connect(lambda: self.delete_requested.emit(workspace))

                # Show menu at cursor position
                menu.exec(self.mapToGlobal(position))


class MainWindow(QMainWindow):
    """Main window for the Workspace File Indexer application."""

    def __init__(self):
        super().__init__()

        # Initialize file table model
        self.file_table_model = FileTableModel()

        self.init_ui()
        self.apply_dark_theme()

    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Workspace File Indexer")
        self.setMinimumSize(QSize(1000, 700))
        self.resize(1200, 800)

        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main horizontal splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        central_widget.setLayout(QHBoxLayout())
        central_widget.layout().addWidget(self.main_splitter)

        # Left area - Workspace List (20-25% width)
        self.left_widget = self.create_left_area()
        self.main_splitter.addWidget(self.left_widget)

        # Right area - Search and File Display
        self.right_widget = self.create_right_area()
        self.main_splitter.addWidget(self.right_widget)

        # Set splitter proportions (left: 25%, right: 75%)
        self.main_splitter.setSizes([300, 900])

    def create_left_area(self):
        """Create the left area containing the workspace list."""
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(15, 15, 15, 15)

        # Title label
        title_label = QLabel("Workspaces")
        title_label.setObjectName("sectionTitle")
        left_layout.addWidget(title_label)

        # Workspace list with database integration
        self.workspace_list = WorkspaceListWidget()
        self.workspace_list.workspace_selected.connect(self._on_workspace_selected)
        self.workspace_list.edit_requested.connect(self._on_edit_workspace)
        self.workspace_list.delete_requested.connect(self._on_delete_workspace)
        left_layout.addWidget(self.workspace_list)

        # Load workspaces from database
        self.workspace_list.load_workspaces()

        # New workspace button
        new_workspace_btn = QPushButton("New Workspace")
        new_workspace_btn.setObjectName("primaryButton")
        new_workspace_btn.clicked.connect(self._on_new_workspace)
        left_layout.addWidget(new_workspace_btn)

        return left_widget

    def _on_workspace_selected(self, workspace: Workspace):
        """Handle workspace selection change."""
        try:
            print(f"Selected workspace: {workspace.name} (ID: {workspace.id})")
            # Load files for the selected workspace into the table model
            self.file_table_model.load_workspace_files(workspace.id)
        except Exception as e:
            QMessageBox.warning(self, "Error Loading Files",
                              f"Failed to load files for workspace '{workspace.name}': {str(e)}")

    def _on_new_workspace(self):
        """Handle new workspace button click."""
        dialog = WorkspaceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            # Refresh workspace list to show the new workspace
            self.workspace_list.refresh()

    def _on_edit_workspace(self, workspace: Workspace):
        """Handle edit workspace request from context menu."""
        dialog = WorkspaceDialog(self, workspace)
        if dialog.exec() == QDialog.Accepted:
            # Refresh workspace list to show updated workspace
            self.workspace_list.refresh()

    def _on_delete_workspace(self, workspace: Workspace):
        """Handle delete workspace request from context menu."""
        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Delete Workspace",
            f"Are you sure you want to delete workspace '{workspace.name}'?\n\n"
            f"This will remove all indexed files and tags for this workspace.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Delete workspace (will cascade to paths, files, and tags)
                Workspace.delete(workspace.id)

                # Refresh workspace list
                self.workspace_list.refresh()

                # Show success message
                QMessageBox.information(
                    self, "Workspace Deleted",
                    f"Workspace '{workspace.name}' has been deleted successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to delete workspace: {str(e)}"
                )

    def create_right_area(self):
        """Create the right area containing search and file display."""
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(15, 15, 15, 15)

        # Search area (top of right panel)
        search_widget = self.create_search_area()
        right_layout.addWidget(search_widget)

        # File display area (bottom of right panel)
        self.file_table = self.create_file_table()
        right_layout.addWidget(self.file_table)

        return right_widget

    def create_search_area(self):
        """Create the search input area."""
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setSpacing(10)
        search_layout.setContentsMargins(0, 0, 0, 0)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files and tags...")
        self.search_input.setObjectName("searchInput")
        search_layout.addWidget(self.search_input, 1)

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self._on_search_clear)
        search_layout.addWidget(clear_btn)

        # Connect search input to trigger search on text change
        self.search_input.textChanged.connect(self._on_search_text_changed)

        return search_widget

    def create_file_table(self):
        """Create the file table view with model."""
        table = QTableView()
        table.setObjectName("fileTable")
        table.setModel(self.file_table_model)

        # Configure table appearance and behavior
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setSortingEnabled(True)
        table.setShowGrid(False)

        # Set custom delegate for tags column to render as pills/badges
        tag_delegate = TagPillDelegate(table)
        table.setItemDelegateForColumn(FileTableModel.COL_TAGS, tag_delegate)

        # Configure column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(FileTableModel.COL_RELATIVE_PATH, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(FileTableModel.COL_FILE_TYPE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(FileTableModel.COL_ABSOLUTE_PATH, QHeaderView.Stretch)
        header.setSectionResizeMode(FileTableModel.COL_TAGS, QHeaderView.ResizeToContents)

        # Configure vertical header
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # Enable context menu for file operations
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_file_context_menu)

        # Set minimum height
        table.setMinimumHeight(200)

        return table

    def _on_search_text_changed(self):
        """Handle search input text change to filter files dynamically."""
        search_text = self.search_input.text().strip()

        # If search is empty, show all files for current workspace
        if not search_text:
            current_workspace = self.workspace_list.get_selected_workspace()
            if current_workspace:
                self.file_table_model.load_workspace_files(current_workspace.id)
            return

        # Parse search text for keywords (support ; or ； separators)
        keywords = [keyword.strip() for keyword in search_text.replace('；', ';').split(';') if keyword.strip()]

        if not keywords:
            return

        # For now, treat all terms as keywords (tags will be enhanced in Phase 8)
        # Use the first keyword as the main search term
        main_keyword = keywords[0]

        try:
            current_workspace = self.workspace_list.get_selected_workspace()
            workspace_id = current_workspace.id if current_workspace else None

            # Search files using the FileEntry search method
            from core.scanner import FileEntry
            filtered_files = FileEntry.search_by_keyword(main_keyword, workspace_id)

            # Update the model with filtered results
            self.file_table_model._set_files(filtered_files)

        except Exception as e:
            QMessageBox.warning(self, "Search Error",
                              f"Failed to search files: {str(e)}")

    def _on_search_clear(self):
        """Handle clear button click to reset search."""
        self.search_input.clear()
        # The textChanged signal will automatically trigger and reload all files

    def _show_file_context_menu(self, position):
        """Show context menu for file table items."""
        # Get the index and file entry at the clicked position
        index = self.file_table.indexAt(position)
        if not index.isValid():
            return

        # Get file entry from the model
        file_entry = self.file_table_model.get_file_at_row(index.row())
        if not file_entry:
            return

        # Create context menu
        menu = QMenu(self)

        # Open File action
        open_action = menu.addAction("Open File")
        open_action.triggered.connect(lambda: self._open_file(file_entry.absolute_path))

        # Reveal in Explorer/Finder action
        reveal_text = "Reveal in Explorer" if platform.system() == "Windows" else "Reveal in Finder"
        reveal_action = menu.addAction(reveal_text)
        reveal_action.triggered.connect(lambda: self._reveal_file(file_entry.absolute_path))

        # Copy File Path action
        copy_action = menu.addAction("Copy File Path")
        copy_action.triggered.connect(lambda: self._copy_file_path(file_entry.absolute_path))

        menu.addSeparator()

        # TODO: Assign/Edit Tags action (will be implemented in a later task)
        # assign_tags_action = menu.addAction("Assign/Edit Tags")
        # assign_tags_action.triggered.connect(lambda: self._assign_tags(file_entry))

        # Delete File action
        delete_action = menu.addAction("Delete File")
        delete_action.triggered.connect(lambda: self._delete_file(file_entry))

        # Remove from Workspace action
        remove_action = menu.addAction("Remove from Workspace")
        remove_action.triggered.connect(lambda: self._remove_from_workspace(file_entry))

        # Show menu at cursor position
        menu.exec(self.file_table.mapToGlobal(position))

    def _open_file(self, file_path):
        """Open file with system default application."""
        try:
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            QMessageBox.warning(self, "Error Opening File",
                              f"Failed to open file: {str(e)}")

    def _reveal_file(self, file_path):
        """Reveal file in system file explorer."""
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", "/select,", file_path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", "-R", file_path])
            else:  # Linux
                # Try common file managers
                file_managers = ["nautilus", "dolphin", "thunar", "pcmanfm"]
                parent_dir = str(Path(file_path).parent)
                for manager in file_managers:
                    try:
                        subprocess.run([manager, parent_dir])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    # Fallback to opening parent directory
                    subprocess.run(["xdg-open", parent_dir])
        except Exception as e:
            QMessageBox.warning(self, "Error Revealing File",
                              f"Failed to reveal file: {str(e)}")

    def _copy_file_path(self, file_path):
        """Copy file path to clipboard."""
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(file_path)

            # Show brief success message
            QMessageBox.information(self, "Path Copied",
                                  f"File path copied to clipboard:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error Copying Path",
                              f"Failed to copy file path: {str(e)}")

    def _delete_file(self, file_entry):
        """Delete file using send2trash for safe deletion."""
        file_path = file_entry.absolute_path

        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Delete File",
            f"Are you sure you want to delete this file?\n\n{file_path}\n\n"
            f"This will move the file to the Recycle Bin/Trash.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Move file to trash using send2trash
                send2trash.send2trash(file_path)

                # Remove file entry from database
                from core.scanner import FileEntry
                FileEntry.delete_by_absolute_path(file_entry.absolute_path)

                # Refresh the current view
                current_workspace = self.workspace_list.get_selected_workspace()
                if current_workspace:
                    if self.search_input.text().strip():
                        # If search is active, re-run search
                        self._on_search_text_changed()
                    else:
                        # Otherwise reload workspace files
                        self.file_table_model.load_workspace_files(current_workspace.id)

                QMessageBox.information(self, "File Deleted",
                                      f"File moved to trash successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error Deleting File",
                                   f"Failed to delete file: {str(e)}")

    def _remove_from_workspace(self, file_entry):
        """Remove file from workspace without deleting the actual file."""
        file_path = file_entry.absolute_path

        # Ask for confirmation
        reply = QMessageBox.question(
            self, "Remove from Workspace",
            f"Remove this file from the workspace index?\n\n{file_path}\n\n"
            f"The actual file will not be deleted.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Remove file entry from database
                from core.scanner import FileEntry
                FileEntry.delete_by_absolute_path(file_entry.absolute_path)

                # Refresh the current view
                current_workspace = self.workspace_list.get_selected_workspace()
                if current_workspace:
                    if self.search_input.text().strip():
                        # If search is active, re-run search
                        self._on_search_text_changed()
                    else:
                        # Otherwise reload workspace files
                        self.file_table_model.load_workspace_files(current_workspace.id)

                QMessageBox.information(self, "File Removed",
                                      f"File removed from workspace index.")
            except Exception as e:
                QMessageBox.critical(self, "Error Removing File",
                                   f"Failed to remove file from workspace: {str(e)}")

    def apply_dark_theme(self):
        """Apply modern dark theme styling similar to VSCode/Cursor."""
        # Color palette
        bg_primary = "#1e1e1e"      # Main background (very dark gray)
        bg_secondary = "#252526"    # Secondary background (slightly lighter)
        bg_tertiary = "#2d2d30"     # Tertiary background (widgets)
        accent_blue = "#007acc"     # Accent color (VSCode blue)
        text_primary = "#cccccc"    # Primary text (light gray)
        text_secondary = "#969696"  # Secondary text (medium gray)
        border_color = "#3e3e42"    # Subtle border color
        hover_color = "#2a2d2e"     # Hover background

        self.setStyleSheet(f"""
            /* Main window */
            QMainWindow {{
                background-color: {bg_primary};
                color: {text_primary};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }}

            /* Central widget and containers */
            QWidget {{
                background-color: {bg_primary};
                color: {text_primary};
            }}

            /* Splitter */
            QSplitter::handle {{
                background-color: {border_color};
                width: 1px;
                height: 1px;
            }}

            QSplitter::handle:hover {{
                background-color: {accent_blue};
            }}

            /* Section titles */
            QLabel#sectionTitle {{
                color: {text_primary};
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 5px;
            }}

            /* Workspace List */
            QListWidget#workspaceList {{
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 5px;
                outline: none;
                selection-background-color: {accent_blue};
            }}

            QListWidget#workspaceList::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 1px 0;
            }}

            QListWidget#workspaceList::item:hover {{
                background-color: {hover_color};
            }}

            QListWidget#workspaceList::item:selected {{
                background-color: {accent_blue};
                color: white;
            }}

            /* Search input */
            QLineEdit#searchInput {{
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: {text_primary};
            }}

            QLineEdit#searchInput:focus {{
                border-color: {accent_blue};
                outline: none;
            }}

            QLineEdit#searchInput::placeholder {{
                color: {text_secondary};
            }}

            /* Primary buttons */
            QPushButton#primaryButton {{
                background-color: {accent_blue};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                color: white;
                font-weight: 500;
                font-size: 13px;
            }}

            QPushButton#primaryButton:hover {{
                background-color: #1177bb;
            }}

            QPushButton#primaryButton:pressed {{
                background-color: #005a9e;
            }}

            /* Secondary buttons */
            QPushButton#secondaryButton {{
                background-color: {bg_tertiary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 6px 12px;
                color: {text_primary};
                font-size: 13px;
            }}

            QPushButton#secondaryButton:hover {{
                background-color: {hover_color};
                border-color: {accent_blue};
            }}

            QPushButton#secondaryButton:pressed {{
                background-color: {bg_secondary};
            }}

            /* File Table */
            QTableView#fileTable {{
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: 6px;
                gridline-color: {border_color};
                selection-background-color: {accent_blue};
                alternate-background-color: {bg_tertiary};
                outline: none;
            }}

            QTableView#fileTable::item {{
                padding: 6px 8px;
                border: none;
            }}

            QTableView#fileTable::item:hover {{
                background-color: {hover_color};
            }}

            QTableView#fileTable::item:selected {{
                background-color: {accent_blue};
                color: white;
            }}

            /* Table Headers */
            QHeaderView::section {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_color};
                border-left: none;
                border-top: none;
                padding: 8px 12px;
                font-weight: bold;
            }}

            QHeaderView::section:first {{
                border-left: 1px solid {border_color};
            }}

            QHeaderView::section:hover {{
                background-color: {hover_color};
            }}
        """)


def main():
    """Entry point for the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Workspace File Indexer")
    app.setOrganizationName("VIBE")

    # Set application icon (if available)
    # app.setWindowIcon(QIcon("icon.png"))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()