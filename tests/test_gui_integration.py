"""Integration tests for GUI components."""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from core.models import Workspace, WorkspacePath
from gui.main_window import MainWindow, WorkspaceListWidget
from gui.dialogs import WorkspaceDialog


class TestGUIIntegration(unittest.TestCase):
    """Test integration between GUI components and database layer."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for GUI tests."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures with temporary database."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Patch the database path
        self.db_patcher = patch('core.db.get_db_path')
        mock_get_db_path = self.db_patcher.start()
        mock_get_db_path.return_value = self.db_path

        # Initialize database
        from core.db import initialize_database
        initialize_database()

    def tearDown(self):
        """Clean up test fixtures."""
        self.db_patcher.stop()
        # Clean up temp database
        Path(self.db_path).unlink(missing_ok=True)

    def test_workspace_list_widget_signals(self):
        """Test that WorkspaceListWidget emits correct signals."""
        # Create test workspace
        workspace = Workspace.create("Test Workspace")

        # Create widget and load data
        widget = WorkspaceListWidget()

        # Set up signal spy
        selected_signals = []
        edit_signals = []
        delete_signals = []

        widget.workspace_selected.connect(lambda w: selected_signals.append(w))
        widget.edit_requested.connect(lambda w: edit_signals.append(w))
        widget.delete_requested.connect(lambda w: delete_signals.append(w))

        # Load workspaces
        widget.load_workspaces()

        # Verify workspace was loaded
        self.assertEqual(widget.count(), 1)
        self.assertEqual(widget.item(0).text(), "Test Workspace")

        # Test selection signal
        widget.setCurrentRow(0)
        self.assertEqual(len(selected_signals), 1)
        self.assertEqual(selected_signals[0].name, "Test Workspace")

        # Test that workspace object is stored correctly
        selected_workspace = widget.get_selected_workspace()
        self.assertIsNotNone(selected_workspace)
        self.assertEqual(selected_workspace.name, "Test Workspace")

    def test_main_window_dialog_integration(self):
        """Test that MainWindow properly integrates with WorkspaceDialog."""
        # Create main window
        main_window = MainWindow()

        # Verify initial state
        initial_count = main_window.workspace_list.count()

        # Test workspace dialog integration by mocking dialog result
        with patch('gui.main_window.WorkspaceDialog') as mock_dialog_class:
            # Mock dialog instance
            mock_dialog = Mock()
            mock_dialog.exec.return_value = WorkspaceDialog.Accepted
            mock_dialog_class.return_value = mock_dialog

            # Create a test workspace to simulate dialog success
            test_workspace = Workspace.create("Dialog Test Workspace")

            # Trigger new workspace dialog
            main_window._on_new_workspace()

            # Verify dialog was created and exec was called
            mock_dialog_class.assert_called_once_with(main_window)
            mock_dialog.exec.assert_called_once()

            # Verify workspace list was refreshed (count should include new workspace)
            self.assertGreaterEqual(main_window.workspace_list.count(), initial_count)

    def test_workspace_dialog_database_integration(self):
        """Test that WorkspaceDialog properly saves to database."""
        # Create dialog for new workspace
        dialog = WorkspaceDialog()

        # Set workspace name
        dialog.name_input.setText("Integration Test Workspace")

        # Add a test path
        test_path = str(Path(__file__).parent)
        dialog.add_path_to_table(test_path, "folder")

        # Verify path was added to dialog
        self.assertEqual(len(dialog.workspace_paths), 1)
        self.assertEqual(dialog.workspace_paths[0].root_path, test_path)
        self.assertEqual(dialog.workspace_paths[0].path_type, "folder")

        # Mock the dialog execution to test save functionality
        with patch.object(dialog, 'accept') as mock_accept:
            dialog.save_workspace()

            # Verify accept was called (indicating successful save)
            mock_accept.assert_called_once()

        # Verify workspace was created in database
        workspaces = Workspace.list_all()
        workspace_names = [w.name for w in workspaces]
        self.assertIn("Integration Test Workspace", workspace_names)

        # Find the created workspace
        created_workspace = None
        for workspace in workspaces:
            if workspace.name == "Integration Test Workspace":
                created_workspace = workspace
                break

        self.assertIsNotNone(created_workspace)

        # Verify workspace paths were created
        workspace_paths = WorkspacePath.get_paths_for_workspace(created_workspace.id)
        self.assertEqual(len(workspace_paths), 1)
        self.assertEqual(workspace_paths[0].root_path, test_path)
        self.assertEqual(workspace_paths[0].path_type, "folder")


if __name__ == '__main__':
    unittest.main()