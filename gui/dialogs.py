"""Dialog windows for the Workspace File Indexer GUI application."""

import os
from pathlib import Path
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QLabel, QWidget
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

# Import core data models
from core.models import Workspace, WorkspacePath


class WorkspaceDialog(QDialog):
    """Dialog for creating new workspaces or editing existing ones."""

    def __init__(self, parent=None, workspace: Optional[Workspace] = None):
        super().__init__(parent)

        self.workspace = workspace  # None for new workspace, Workspace object for editing
        self.workspace_paths = []  # List of WorkspacePath objects

        self.init_ui()
        self.apply_theme()

        if self.workspace:
            self.load_existing_workspace()

    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        title = "Edit Workspace" if self.workspace else "New Workspace"
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumSize(QSize(600, 500))
        self.resize(700, 600)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")
        main_layout.addWidget(title_label)

        # Workspace name section
        name_section = self.create_name_section()
        main_layout.addWidget(name_section)

        # Paths section
        paths_section = self.create_paths_section()
        main_layout.addWidget(paths_section, 1)  # Expand this section

        # Buttons section
        buttons_section = self.create_buttons_section()
        main_layout.addWidget(buttons_section)

    def create_name_section(self) -> QWidget:
        """Create the workspace name input section."""
        section = QWidget()
        layout = QFormLayout(section)
        layout.setSpacing(10)

        # Workspace name input
        self.name_input = QLineEdit()
        self.name_input.setObjectName("nameInput")
        self.name_input.setPlaceholderText("Enter workspace name...")
        layout.addRow("Workspace Name:", self.name_input)

        return section

    def create_paths_section(self) -> QWidget:
        """Create the paths management section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(10)

        # Section title
        paths_label = QLabel("Workspace Paths")
        paths_label.setObjectName("sectionLabel")
        layout.addWidget(paths_label)

        # Add path buttons
        add_buttons_layout = QHBoxLayout()

        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.setObjectName("secondaryButton")
        self.add_folder_btn.clicked.connect(self.add_folder)
        add_buttons_layout.addWidget(self.add_folder_btn)

        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.setObjectName("secondaryButton")
        self.add_file_btn.clicked.connect(self.add_file)
        add_buttons_layout.addWidget(self.add_file_btn)

        add_buttons_layout.addStretch()
        layout.addLayout(add_buttons_layout)

        # Paths table
        self.paths_table = QTableWidget()
        self.paths_table.setObjectName("pathsTable")
        self.paths_table.setColumnCount(3)
        self.paths_table.setHorizontalHeaderLabels(["Type", "Path", ""])

        # Configure table columns
        header = self.paths_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Type column
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Path column
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Remove button column

        self.paths_table.verticalHeader().setVisible(False)
        self.paths_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.paths_table.setAlternatingRowColors(True)

        layout.addWidget(self.paths_table)

        return section

    def create_buttons_section(self) -> QWidget:
        """Create the dialog buttons section."""
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.addStretch()

        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)

        # Save button
        save_text = "Update" if self.workspace else "Create"
        self.save_btn = QPushButton(save_text)
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self.save_workspace)
        layout.addWidget(self.save_btn)

        return section

    def load_existing_workspace(self):
        """Load data for an existing workspace being edited."""
        if not self.workspace:
            return

        # Set workspace name
        self.name_input.setText(self.workspace.name)

        # Load workspace paths
        try:
            self.workspace_paths = WorkspacePath.get_paths_for_workspace(self.workspace.id)
            self.refresh_paths_table()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load workspace paths: {str(e)}")

    def add_folder(self):
        """Open directory picker to add a folder path."""
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder to Add to Workspace",
            os.path.expanduser("~")
        )

        if folder_path:
            self.add_path_to_table(folder_path, "folder")

    def add_file(self):
        """Open file picker to add a file path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Add to Workspace",
            os.path.expanduser("~"),
            "All Files (*)"
        )

        if file_path:
            self.add_path_to_table(file_path, "file")

    def add_path_to_table(self, path: str, path_type: str):
        """Add a path to the paths table."""
        # Check for duplicates
        for workspace_path in self.workspace_paths:
            if workspace_path.root_path == path:
                QMessageBox.information(self, "Duplicate Path",
                                      "This path is already added to the workspace.")
                return

        # Create temporary WorkspacePath object (ID will be None for new paths)
        workspace_path = WorkspacePath(
            id=None,
            workspace_id=self.workspace.id if self.workspace else 0,
            root_path=path,
            path_type=path_type
        )

        self.workspace_paths.append(workspace_path)
        self.refresh_paths_table()

    def refresh_paths_table(self):
        """Refresh the paths table display."""
        self.paths_table.setRowCount(len(self.workspace_paths))

        for row, workspace_path in enumerate(self.workspace_paths):
            # Type column
            type_item = QTableWidgetItem(workspace_path.path_type.title())
            type_item.setTextAlignment(Qt.AlignCenter)
            self.paths_table.setItem(row, 0, type_item)

            # Path column
            path_item = QTableWidgetItem(workspace_path.root_path)
            path_item.setToolTip(workspace_path.root_path)  # Show full path on hover
            self.paths_table.setItem(row, 1, path_item)

            # Remove button column
            remove_btn = QPushButton("Remove")
            remove_btn.setObjectName("dangerButton")
            remove_btn.clicked.connect(lambda checked, r=row: self.remove_path(r))
            self.paths_table.setCellWidget(row, 2, remove_btn)

    def remove_path(self, row: int):
        """Remove a path from the workspace."""
        if 0 <= row < len(self.workspace_paths):
            path_to_remove = self.workspace_paths[row]

            # Ask for confirmation
            reply = QMessageBox.question(
                self, "Remove Path",
                f"Remove this path from the workspace?\n\n{path_to_remove.root_path}",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.workspace_paths.pop(row)
                self.refresh_paths_table()

    def save_workspace(self):
        """Save the workspace and its paths to the database."""
        # Validate workspace name
        workspace_name = self.name_input.text().strip()
        if not workspace_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a workspace name.")
            self.name_input.setFocus()
            return

        # Check if at least one path is added
        if not self.workspace_paths:
            reply = QMessageBox.question(
                self, "No Paths",
                "No paths have been added to this workspace. Continue anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        try:
            if self.workspace:
                # Update existing workspace
                self.workspace.name = workspace_name
                # Note: Workspace.update() method would need to be implemented
                # For now, we'll handle this in Phase 6 completion
                workspace_id = self.workspace.id
            else:
                # Create new workspace
                new_workspace = Workspace.create(workspace_name)
                workspace_id = new_workspace.id

            # Handle workspace paths
            if self.workspace:
                # For existing workspace, we need to sync paths
                # Get current paths from database
                existing_paths = WorkspacePath.get_paths_for_workspace(workspace_id)

                # Remove paths that are no longer in our list
                for existing_path in existing_paths:
                    found = False
                    for current_path in self.workspace_paths:
                        if (current_path.id == existing_path.id or
                            (current_path.id is None and
                             current_path.root_path == existing_path.root_path)):
                            found = True
                            break

                    if not found:
                        WorkspacePath.remove_path(workspace_id, existing_path.root_path)

            # Add new paths
            for workspace_path in self.workspace_paths:
                if workspace_path.id is None:  # New path
                    WorkspacePath.add_path(workspace_id, workspace_path.root_path, workspace_path.path_type)

            self.accept()  # Close dialog with success

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save workspace: {str(e)}")

    def apply_theme(self):
        """Apply dark theme styling consistent with main window."""
        # Color palette (matching main_window.py)
        bg_primary = "#1e1e1e"      # Main background
        bg_secondary = "#252526"    # Secondary background
        bg_tertiary = "#2d2d30"     # Tertiary background
        accent_blue = "#007acc"     # Accent color
        text_primary = "#cccccc"    # Primary text
        text_secondary = "#969696"  # Secondary text
        border_color = "#3e3e42"    # Border color
        hover_color = "#2a2d2e"     # Hover background
        danger_color = "#d73027"    # Danger/remove button color

        self.setStyleSheet(f"""
            /* Dialog */
            QDialog {{
                background-color: {bg_primary};
                color: {text_primary};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }}

            /* Dialog title */
            QLabel#dialogTitle {{
                color: {text_primary};
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 10px;
            }}

            /* Section labels */
            QLabel#sectionLabel {{
                color: {text_primary};
                font-size: 14px;
                font-weight: 600;
                margin: 5px 0;
            }}

            /* Name input */
            QLineEdit#nameInput {{
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: {text_primary};
            }}

            QLineEdit#nameInput:focus {{
                border-color: {accent_blue};
                outline: none;
            }}

            QLineEdit#nameInput::placeholder {{
                color: {text_secondary};
            }}

            /* Paths table */
            QTableWidget#pathsTable {{
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: 6px;
                gridline-color: {border_color};
                selection-background-color: {accent_blue};
                alternate-background-color: {bg_tertiary};
            }}

            QTableWidget#pathsTable::item {{
                padding: 8px;
                border: none;
            }}

            QTableWidget#pathsTable::item:selected {{
                background-color: {accent_blue};
                color: white;
            }}

            QHeaderView::section {{
                background-color: {bg_tertiary};
                color: {text_primary};
                border: 1px solid {border_color};
                padding: 8px;
                font-weight: 600;
            }}

            /* Primary buttons */
            QPushButton#primaryButton {{
                background-color: {accent_blue};
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                color: white;
                font-weight: 500;
                font-size: 13px;
                min-width: 80px;
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
                padding: 8px 16px;
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

            /* Danger buttons */
            QPushButton#dangerButton {{
                background-color: {danger_color};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                color: white;
                font-size: 12px;
            }}

            QPushButton#dangerButton:hover {{
                background-color: #c92a2a;
            }}

            QPushButton#dangerButton:pressed {{
                background-color: #a61e1e;
            }}

            /* Form layout labels */
            QFormLayout QLabel {{
                color: {text_primary};
                font-weight: 500;
            }}
        """)