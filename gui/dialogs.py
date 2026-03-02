"""Dialog windows for the Workspace File Indexer GUI application."""

import os
from pathlib import Path
from typing import Optional, List, Set
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QFileDialog, QLabel, QWidget,
    QCompleter, QScrollArea, QFrame, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QSize, QStringListModel, QTimer
from PySide6.QtGui import QFont, QIcon, QPalette, QPainter, QFontMetrics

# Import core data models
from core.models import Workspace, WorkspacePath, Tag
from core.scanner import FileEntry


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
            remove_btn.setMinimumWidth(80)  # Ensure button is wide enough for text
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
                padding: 6px 12px;
                color: white;
                font-size: 12px;
                min-width: 70px;
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


class TagPillWidget(QWidget):
    """Widget to display a tag as a removable pill/badge."""

    def __init__(self, tag_name: str, parent=None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.removable = True
        self.init_ui()

    def init_ui(self):
        """Initialize the tag pill UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # Tag label
        self.tag_label = QLabel(self.tag_name)
        self.tag_label.setObjectName("tagLabel")
        layout.addWidget(self.tag_label)

        # Remove button
        if self.removable:
            self.remove_btn = QPushButton("×")
            self.remove_btn.setObjectName("tagRemoveButton")
            self.remove_btn.setFixedSize(16, 16)
            self.remove_btn.clicked.connect(self.remove_requested)
            layout.addWidget(self.remove_btn)

        self.setFixedHeight(24)
        self.apply_pill_style()

    def remove_requested(self):
        """Signal that this tag should be removed."""
        if self.parent() and hasattr(self.parent(), '_remove_tag_pill'):
            self.parent()._remove_tag_pill(self)

    def apply_pill_style(self):
        """Apply pill/badge styling to the widget."""
        # Generate color based on tag name hash (similar to TagPillDelegate)
        colors = [
            "#e74c3c", "#3498db", "#2ecc71", "#f39c12",
            "#9b59b6", "#1abc9c", "#e67e22", "#34495e",
            "#e91e63", "#ff9800"
        ]
        color = colors[hash(self.tag_name) % len(colors)]

        # Calculate contrasting text color
        text_color = "#ffffff" if self._is_dark_color(color) else "#000000"

        self.setStyleSheet(f"""
            TagPillWidget {{
                background-color: {color};
                border-radius: 12px;
                margin: 2px;
            }}
            QLabel#tagLabel {{
                color: {text_color};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
            QPushButton#tagRemoveButton {{
                background: transparent;
                border: none;
                color: {text_color};
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
            }}
            QPushButton#tagRemoveButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
        """)

    def _is_dark_color(self, color_hex: str) -> bool:
        """Determine if a color is dark (for text contrast)."""
        color_hex = color_hex.lstrip('#')
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        return brightness < 128


class TagDialog(QDialog):
    """Dialog for assigning, editing, and removing tags for selected files."""

    def __init__(self, parent=None, file_entry: Optional[FileEntry] = None):
        super().__init__(parent)

        self.file_entry = file_entry
        self.current_tags: Set[str] = set()
        self.original_tags: Set[str] = set()
        self.all_existing_tags: List[str] = []

        self.init_ui()
        self.apply_theme()
        self.load_existing_data()

    def init_ui(self):
        """Initialize the user interface."""
        # Set window properties
        self.setWindowTitle("Assign/Edit Tags")
        self.setModal(True)
        self.setMinimumSize(QSize(500, 400))
        self.resize(600, 500)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title and file info
        title_section = self.create_title_section()
        main_layout.addWidget(title_section)

        # Current tags section
        current_tags_section = self.create_current_tags_section()
        main_layout.addWidget(current_tags_section, 1)  # Expand this section

        # Add new tag section
        add_tag_section = self.create_add_tag_section()
        main_layout.addWidget(add_tag_section)

        # Buttons section
        buttons_section = self.create_buttons_section()
        main_layout.addWidget(buttons_section)

    def create_title_section(self) -> QWidget:
        """Create the title and file info section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(5)

        # Dialog title
        title_label = QLabel("Assign/Edit Tags")
        title_label.setObjectName("dialogTitle")
        layout.addWidget(title_label)

        # File info
        if self.file_entry:
            file_info = QLabel(f"File: {self.file_entry.relative_path}")
            file_info.setObjectName("fileInfo")
            file_info.setWordWrap(True)
            layout.addWidget(file_info)

        return section

    def create_current_tags_section(self) -> QWidget:
        """Create the current tags display section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(10)

        # Section title
        tags_label = QLabel("Current Tags")
        tags_label.setObjectName("sectionLabel")
        layout.addWidget(tags_label)

        # Scrollable area for tag pills
        scroll_area = QScrollArea()
        scroll_area.setObjectName("tagScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setMinimumHeight(150)

        # Container widget for tag pills
        self.tags_container = QWidget()
        self.tags_container.setObjectName("tagsContainer")
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setSpacing(5)
        self.tags_layout.setAlignment(Qt.AlignTop)

        scroll_area.setWidget(self.tags_container)
        layout.addWidget(scroll_area)

        return section

    def create_add_tag_section(self) -> QWidget:
        """Create the add new tag section."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setSpacing(10)

        # Section title
        add_label = QLabel("Add New Tag")
        add_label.setObjectName("sectionLabel")
        layout.addWidget(add_label)

        # Input and button layout
        input_layout = QHBoxLayout()

        # Tag input with auto-completion
        self.tag_input = QLineEdit()
        self.tag_input.setObjectName("tagInput")
        self.tag_input.setPlaceholderText("Type tag name...")
        self.tag_input.returnPressed.connect(self.add_tag)
        input_layout.addWidget(self.tag_input, 1)

        # Add button
        self.add_btn = QPushButton("Add")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self.add_tag)
        input_layout.addWidget(self.add_btn)

        layout.addLayout(input_layout)

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

        # Apply button
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setObjectName("primaryButton")
        self.apply_btn.clicked.connect(self.apply_changes)
        layout.addWidget(self.apply_btn)

        return section

    def load_existing_data(self):
        """Load existing tags for the file and all tags for auto-completion."""
        if not self.file_entry:
            return

        try:
            # Load current file tags
            file_tags = Tag.get_tags_for_file(self.file_entry.id)
            self.current_tags = {tag.tag_name for tag in file_tags}
            self.original_tags = self.current_tags.copy()

            # Load all existing tags for auto-completion
            self.all_existing_tags = Tag.get_all_unique_tags()

            # Set up auto-completion
            completer = QCompleter(self.all_existing_tags)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            completer.setCompletionMode(QCompleter.PopupCompletion)
            self.tag_input.setCompleter(completer)

            # Refresh the tags display
            self.refresh_tags_display()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load tag data: {str(e)}")

    def refresh_tags_display(self):
        """Refresh the visual display of current tags."""
        # Clear existing tag widgets
        for i in reversed(range(self.tags_layout.count())):
            child = self.tags_layout.itemAt(i).widget()
            if child:
                child.deleteLater()

        # Add tag pills for current tags
        if self.current_tags:
            # Create a flow layout for tag pills
            current_row_layout = QHBoxLayout()
            current_row_layout.setSpacing(5)
            current_row_layout.setAlignment(Qt.AlignLeft)

            row_width = 0
            max_width = 400  # Approximate container width

            for tag_name in sorted(self.current_tags):
                tag_pill = TagPillWidget(tag_name, self)

                # Estimate pill width (rough calculation)
                pill_width = len(tag_name) * 8 + 40  # Rough estimate

                # If this pill would exceed row width, start a new row
                if row_width + pill_width > max_width and row_width > 0:
                    # Add current row to layout
                    row_widget = QWidget()
                    row_widget.setLayout(current_row_layout)
                    self.tags_layout.addWidget(row_widget)

                    # Start new row
                    current_row_layout = QHBoxLayout()
                    current_row_layout.setSpacing(5)
                    current_row_layout.setAlignment(Qt.AlignLeft)
                    row_width = 0

                current_row_layout.addWidget(tag_pill)
                row_width += pill_width

            # Add the last row
            if current_row_layout.count() > 0:
                current_row_layout.addStretch()  # Push pills to the left
                row_widget = QWidget()
                row_widget.setLayout(current_row_layout)
                self.tags_layout.addWidget(row_widget)
        else:
            # Show "No tags" message
            no_tags_label = QLabel("No tags assigned")
            no_tags_label.setObjectName("noTagsLabel")
            no_tags_label.setAlignment(Qt.AlignCenter)
            self.tags_layout.addWidget(no_tags_label)

        # Add stretch to push content to top
        self.tags_layout.addStretch()

    def _remove_tag_pill(self, tag_pill: TagPillWidget):
        """Remove a tag from the current tags set."""
        if tag_pill.tag_name in self.current_tags:
            self.current_tags.remove(tag_pill.tag_name)
            self.refresh_tags_display()

    def add_tag(self):
        """Add a new tag from the input field."""
        tag_name = self.tag_input.text().strip()

        if not tag_name:
            QMessageBox.warning(self, "Invalid Tag", "Please enter a tag name.")
            self.tag_input.setFocus()
            return

        if tag_name in self.current_tags:
            QMessageBox.information(self, "Duplicate Tag", "This tag is already assigned to the file.")
            self.tag_input.clear()
            self.tag_input.setFocus()
            return

        # Add the tag
        self.current_tags.add(tag_name)
        self.tag_input.clear()
        self.refresh_tags_display()
        self.tag_input.setFocus()

    def apply_changes(self):
        """Apply tag changes to the database."""
        if not self.file_entry:
            self.reject()
            return

        try:
            # Determine which tags to add and remove
            tags_to_add = self.current_tags - self.original_tags
            tags_to_remove = self.original_tags - self.current_tags

            # Remove tags
            for tag_name in tags_to_remove:
                Tag.remove_tag_from_file(self.file_entry.id, tag_name)

            # Add tags
            for tag_name in tags_to_add:
                Tag.add_tag_to_file(self.file_entry.id, tag_name)

            self.accept()  # Close dialog with success

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save tag changes: {str(e)}")

    def apply_theme(self):
        """Apply dark theme styling consistent with main window."""
        # Color palette (matching main_window.py and WorkspaceDialog)
        bg_primary = "#1e1e1e"      # Main background
        bg_secondary = "#252526"    # Secondary background
        bg_tertiary = "#2d2d30"     # Tertiary background
        accent_blue = "#007acc"     # Accent color
        text_primary = "#cccccc"    # Primary text
        text_secondary = "#969696"  # Secondary text
        border_color = "#3e3e42"    # Border color
        hover_color = "#2a2d2e"     # Hover background

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
                margin-bottom: 5px;
            }}

            /* File info */
            QLabel#fileInfo {{
                color: {text_secondary};
                font-size: 12px;
                margin-bottom: 10px;
            }}

            /* Section labels */
            QLabel#sectionLabel {{
                color: {text_primary};
                font-size: 14px;
                font-weight: 600;
                margin: 5px 0;
            }}

            /* Tag input */
            QLineEdit#tagInput {{
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                color: {text_primary};
            }}

            QLineEdit#tagInput:focus {{
                border-color: {accent_blue};
                outline: none;
            }}

            QLineEdit#tagInput::placeholder {{
                color: {text_secondary};
            }}

            /* Scroll area for tags */
            QScrollArea#tagScrollArea {{
                background-color: {bg_secondary};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}

            /* Tags container */
            QWidget#tagsContainer {{
                background-color: transparent;
            }}

            /* No tags label */
            QLabel#noTagsLabel {{
                color: {text_secondary};
                font-style: italic;
                margin: 20px;
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
        """)