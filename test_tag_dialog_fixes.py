#!/usr/bin/env python3
"""Test script to verify Bug Fixes 0011 - Tag dialog layout and text color improvements."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from core.models import Workspace, WorkspacePath, Tag
from core.scanner import FileEntry, scan_workspace
from gui.dialogs import TagDialog
import tempfile

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tag Dialog Test - Bug Fixes 0011")
        self.setGeometry(100, 100, 300, 200)

        # Set up test data
        self.setup_test_data()

        # Create UI
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        test_btn = QPushButton("Test Tag Dialog (with predefined tags)")
        test_btn.clicked.connect(self.test_tag_dialog_with_tags)
        layout.addWidget(test_btn)

        empty_test_btn = QPushButton("Test Tag Dialog (empty)")
        empty_test_btn.clicked.connect(self.test_tag_dialog_empty)
        layout.addWidget(empty_test_btn)

        # Apply basic dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QPushButton {
                background-color: #007acc;
                border: none;
                border-radius: 6px;
                padding: 10px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)

    def setup_test_data(self):
        """Set up test workspace and file entry with various tags."""
        try:
            # Create test workspace
            workspace = Workspace.create("Tag Dialog Test Workspace")

            # Create temporary test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Test file content for tag dialog testing")
                self.test_file_path = f.name

            # Add workspace path
            WorkspacePath.add_path(workspace.id, os.path.dirname(self.test_file_path), "folder")

            # Scan workspace to create file entry
            scan_workspace(workspace.id)

            # Get the file entry
            self.file_entry = FileEntry.get_by_absolute_path(self.test_file_path)

            if self.file_entry:
                # Add various test tags to verify layout and text color
                test_tags = [
                    "bug", "urgent", "frontend", "backend", "ui", "ux",
                    "feature", "enhancement", "documentation", "test",
                    "refactor", "performance", "security", "accessibility"
                ]

                for tag in test_tags:
                    Tag.add_tag_to_file(self.file_entry.id, tag)

        except Exception as e:
            print(f"Error setting up test data: {e}")
            self.file_entry = None

    def test_tag_dialog_with_tags(self):
        """Test tag dialog with predefined tags."""
        if self.file_entry:
            dialog = TagDialog(self, self.file_entry)
            dialog.exec()
        else:
            print("No file entry available for testing")

    def test_tag_dialog_empty(self):
        """Test tag dialog with empty file (no tags)."""
        if self.file_entry:
            # Clear all tags first
            try:
                existing_tags = Tag.get_tags_for_file(self.file_entry.id)
                for tag in existing_tags:
                    Tag.remove_tag_from_file(self.file_entry.id, tag.tag_name)

                dialog = TagDialog(self, self.file_entry)
                dialog.exec()

                # Restore tags for next test
                test_tags = [
                    "bug", "urgent", "frontend", "backend", "ui", "ux",
                    "feature", "enhancement", "documentation", "test"
                ]
                for tag in test_tags:
                    Tag.add_tag_to_file(self.file_entry.id, tag)

            except Exception as e:
                print(f"Error in empty test: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Initialize database
    from core.db import initialize_database
    initialize_database()

    window = TestWindow()
    window.show()

    print("Test Instructions:")
    print("1. Click 'Test Tag Dialog (with predefined tags)' to see layout alignment fixes")
    print("2. Verify that tags are consistently aligned to top-left")
    print("3. Verify that all tag text is white and readable")
    print("4. Add/remove tags to test layout stability")
    print("5. Click 'Test Tag Dialog (empty)' to test the no-tags state")

    sys.exit(app.exec())