"""Main window for the Workspace File Indexer GUI application."""

import sys
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QListWidget, QLineEdit, QPushButton, QLabel, QListWidgetItem,
    QMessageBox, QMenu, QDialog
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QFont, QIcon

# Import core data models
from core.models import Workspace

# Import dialog windows
from gui.dialogs import WorkspaceDialog


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
        print(f"Selected workspace: {workspace.name} (ID: {workspace.id})")
        # TODO: Update file display in Phase 7

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
        file_display_label = QLabel("File display area (coming in Phase 7)")
        file_display_label.setObjectName("placeholderText")
        file_display_label.setAlignment(Qt.AlignCenter)
        file_display_label.setMinimumHeight(200)
        right_layout.addWidget(file_display_label)

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
        search_layout.addWidget(clear_btn)

        return search_widget

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

            /* Placeholder text */
            QLabel#placeholderText {{
                color: {text_secondary};
                font-size: 14px;
                background-color: {bg_secondary};
                border: 1px dashed {border_color};
                border-radius: 6px;
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