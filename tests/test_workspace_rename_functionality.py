"""Tests for workspace rename functionality in GUI dialogs."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Import modules under test
from gui.dialogs import WorkspaceDialog
from core.models import Workspace
from core.db import initialize_database


class TestWorkspaceRenameFunctionality(unittest.TestCase):
    """Test cases for workspace rename functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Create QApplication instance (required for GUI components)
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """Set up test database and sample data."""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / 'test_workspace_rename.db'

        # Patch get_db_path to use our test database
        self.db_patcher = patch('core.db.get_db_path')
        self.mock_get_db_path = self.db_patcher.start()
        self.mock_get_db_path.return_value = self.db_path

        # Initialize test database
        initialize_database()

        # Create test workspace
        self.original_workspace = Workspace.create("Original Workspace")

    def tearDown(self):
        """Clean up test environment."""
        self.db_patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.temp_dir).rmdir()

    def test_workspace_rename_updates_database(self):
        """Test that renaming a workspace updates the database properly."""
        # Create dialog with existing workspace
        dialog = WorkspaceDialog(workspace=self.original_workspace)

        # Simulate user entering new name
        new_name = "Renamed Workspace"
        dialog.name_input.setText(new_name)

        # Start with empty paths list for this test (dialog starts with existing workspace paths)
        dialog.workspace_paths = []

        # Mock message box to avoid UI interaction
        with patch('gui.dialogs.QMessageBox') as mock_msgbox:
            mock_msgbox.question.return_value = 16384  # QMessageBox.Yes
            mock_msgbox.Yes = 16384

            # Call accept (simulates OK button click)
            dialog.accept()

        # Verify workspace was updated in database
        updated_workspace = Workspace.get_by_id(self.original_workspace.id)
        self.assertIsNotNone(updated_workspace)
        self.assertEqual(updated_workspace.name, new_name)

        # Verify the original workspace object was also updated
        self.assertEqual(self.original_workspace.name, new_name)

    def test_workspace_rename_with_duplicate_name_fails(self):
        """Test that renaming to an existing workspace name fails properly."""
        # Create another workspace with the target name
        existing_workspace = Workspace.create("Existing Workspace")

        # Create dialog with original workspace
        dialog = WorkspaceDialog(workspace=self.original_workspace)

        # Try to rename to existing workspace name
        dialog.name_input.setText(existing_workspace.name)

        # Start with empty paths list for this test
        dialog.workspace_paths = []

        # Mock message box interactions
        with patch('gui.dialogs.QMessageBox') as mock_msgbox:
            # First message box for confirmation
            mock_msgbox.question.return_value = 16384  # QMessageBox.Yes
            mock_msgbox.Yes = 16384

            # Second message box for error
            mock_msgbox.critical = Mock()

            # Call accept - should fail due to duplicate name
            dialog.accept()

            # Verify error message was shown
            mock_msgbox.critical.assert_called_once()
            error_args = mock_msgbox.critical.call_args
            self.assertIn("already exists", error_args[0][1].lower())  # Error message should mention "already exists"

        # Verify original workspace name was not changed
        unchanged_workspace = Workspace.get_by_id(self.original_workspace.id)
        self.assertEqual(unchanged_workspace.name, "Original Workspace")

    def test_workspace_creation_still_works(self):
        """Test that workspace creation (not renaming) still works properly."""
        # Create dialog for new workspace (no existing workspace)
        dialog = WorkspaceDialog()

        # Set name for new workspace
        new_name = "Brand New Workspace"
        dialog.name_input.setText(new_name)

        # Start with empty paths list
        dialog.workspace_paths = []

        # Mock message box
        with patch('gui.dialogs.QMessageBox') as mock_msgbox:
            mock_msgbox.question.return_value = 16384  # QMessageBox.Yes
            mock_msgbox.Yes = 16384

            # Call accept
            dialog.accept()

        # Verify new workspace was created
        new_workspace = Workspace.get_by_name(new_name)
        self.assertIsNotNone(new_workspace)
        self.assertEqual(new_workspace.name, new_name)

    def test_dialog_initializes_with_existing_workspace_name(self):
        """Test that dialog shows existing workspace name when editing."""
        dialog = WorkspaceDialog(workspace=self.original_workspace)

        # Verify the name input is pre-filled
        self.assertEqual(dialog.name_input.text(), self.original_workspace.name)

        # Verify the dialog title indicates editing
        self.assertIn("Edit", dialog.windowTitle())

    def test_dialog_initializes_for_new_workspace(self):
        """Test that dialog is properly set up for new workspace creation."""
        dialog = WorkspaceDialog()

        # Verify the name input is empty
        self.assertEqual(dialog.name_input.text(), "")

        # Verify the dialog title indicates creation
        self.assertIn("New", dialog.windowTitle())


if __name__ == '__main__':
    unittest.main()