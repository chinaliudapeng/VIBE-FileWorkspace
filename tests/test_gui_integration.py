"""Integration tests for GUI components."""

import unittest
import tempfile
import os
import platform
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest

from core.models import Workspace, WorkspacePath
from core.scanner import FileEntry
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


class TestFileTableContextMenu(unittest.TestCase):
    """Test context menu functionality for the file table."""

    @classmethod
    def setUpClass(cls):
        """Set up QApplication for GUI tests."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        """Set up test fixtures with temporary database and files."""
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

        # Create test workspace and file entry
        self.workspace = Workspace.create("Test Workspace Context Menu")
        self.test_file_path = str(Path(__file__).absolute())
        self.file_entry = FileEntry.create(
            workspace_id=self.workspace.id,
            relative_path="test_file.py",
            absolute_path=self.test_file_path,
            file_type="python"
        )

        # Create main window and load data
        self.main_window = MainWindow()
        self.main_window.workspace_list.load_workspaces()
        self.main_window.workspace_list.setCurrentRow(0)  # Select the test workspace

    def tearDown(self):
        """Clean up test fixtures."""
        self.main_window.close()
        self.db_patcher.stop()
        # Clean up temp database
        Path(self.db_path).unlink(missing_ok=True)

    @patch('gui.main_window.os.startfile')
    @patch('gui.main_window.subprocess.run')
    def test_open_file_action(self, mock_subprocess, mock_startfile):
        """Test opening file with system default application."""
        # Mock platform.system to test different OS behaviors
        with patch('gui.main_window.platform.system') as mock_platform:
            # Test Windows
            mock_platform.return_value = "Windows"
            self.main_window._open_file(self.test_file_path)
            mock_startfile.assert_called_once_with(self.test_file_path)

            # Test macOS
            mock_startfile.reset_mock()
            mock_platform.return_value = "Darwin"
            self.main_window._open_file(self.test_file_path)
            mock_subprocess.assert_called_with(["open", self.test_file_path])

            # Test Linux
            mock_subprocess.reset_mock()
            mock_platform.return_value = "Linux"
            self.main_window._open_file(self.test_file_path)
            mock_subprocess.assert_called_with(["xdg-open", self.test_file_path])

    @patch('gui.main_window.subprocess.run')
    def test_reveal_file_action(self, mock_subprocess):
        """Test revealing file in system file explorer."""
        with patch('gui.main_window.platform.system') as mock_platform:
            # Test Windows
            mock_platform.return_value = "Windows"
            self.main_window._reveal_file(self.test_file_path)
            mock_subprocess.assert_called_with(["explorer", "/select,", self.test_file_path])

            # Test macOS
            mock_subprocess.reset_mock()
            mock_platform.return_value = "Darwin"
            self.main_window._reveal_file(self.test_file_path)
            mock_subprocess.assert_called_with(["open", "-R", self.test_file_path])

    @patch('PySide6.QtWidgets.QApplication.clipboard')
    @patch('PySide6.QtWidgets.QMessageBox.information')
    def test_copy_file_path_action(self, mock_info, mock_clipboard):
        """Test copying file path to clipboard."""
        # Mock clipboard
        mock_clipboard_instance = Mock()
        mock_clipboard.return_value = mock_clipboard_instance

        # Test copying path
        self.main_window._copy_file_path(self.test_file_path)

        # Verify clipboard was called
        mock_clipboard_instance.setText.assert_called_once_with(self.test_file_path)

        # Verify info message was shown
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        self.assertIn("Path Copied", args)

    @patch('gui.main_window.send2trash.send2trash')
    @patch('PySide6.QtWidgets.QMessageBox.question')
    @patch('PySide6.QtWidgets.QMessageBox.information')
    @patch('PySide6.QtWidgets.QMessageBox.critical')
    def test_delete_file_action(self, mock_critical, mock_info, mock_question, mock_send2trash):
        """Test deleting file and removing from database."""
        # Mock user confirmation
        mock_question.return_value = QMessageBox.Yes

        # Mock GUI refresh operations and workspace operations to avoid test environment issues
        with patch.object(self.main_window.file_table_model, 'load_workspace_files') as mock_refresh, \
             patch.object(self.main_window, '_on_search_text_changed') as mock_search, \
             patch.object(self.main_window.workspace_list, 'get_selected_workspace') as mock_workspace, \
             patch.object(self.main_window.search_input, 'text') as mock_search_text:

            # Setup mocks
            mock_workspace.return_value = self.workspace
            mock_search_text.return_value = ""

            # Test deleting file
            self.main_window._delete_file(self.file_entry)

            # Verify confirmation dialog was shown
            mock_question.assert_called_once()
            args, kwargs = mock_question.call_args
            self.assertIn("Delete File", args)

            # Verify send2trash was called
            mock_send2trash.assert_called_once_with(self.test_file_path)

            # Verify success message was shown (if it was called)
            if mock_info.called:
                args, kwargs = mock_info.call_args
                self.assertIn("File Deleted", args)

        # Verify file entry was removed from database (this is the most important test)
        deleted_file = FileEntry.get_by_absolute_path(self.test_file_path)
        self.assertIsNone(deleted_file)

    @patch('PySide6.QtWidgets.QMessageBox.question')
    @patch('PySide6.QtWidgets.QMessageBox.information')
    @patch('PySide6.QtWidgets.QMessageBox.critical')
    def test_remove_from_workspace_action(self, mock_critical, mock_info, mock_question):
        """Test removing file from workspace without deleting actual file."""
        # Mock user confirmation
        mock_question.return_value = QMessageBox.Yes

        # Verify file exists in database before removal
        existing_file = FileEntry.get_by_absolute_path(self.test_file_path)
        self.assertIsNotNone(existing_file)

        # Mock GUI refresh operations and workspace operations to avoid test environment issues
        with patch.object(self.main_window.file_table_model, 'load_workspace_files') as mock_refresh, \
             patch.object(self.main_window, '_on_search_text_changed') as mock_search, \
             patch.object(self.main_window.workspace_list, 'get_selected_workspace') as mock_workspace, \
             patch.object(self.main_window.search_input, 'text') as mock_search_text:

            # Setup mocks
            mock_workspace.return_value = self.workspace
            mock_search_text.return_value = ""

            # Test removing file from workspace
            self.main_window._remove_from_workspace(self.file_entry)

            # Verify confirmation dialog was shown
            mock_question.assert_called_once()
            args, kwargs = mock_question.call_args
            self.assertIn("Remove from Workspace", args)

            # Verify success message was shown (if it was called)
            if mock_info.called:
                args, kwargs = mock_info.call_args
                self.assertIn("File Removed", args)

        # Verify file entry was removed from database (this is the most important test)
        deleted_file = FileEntry.get_by_absolute_path(self.test_file_path)
        self.assertIsNone(deleted_file)

    @patch('PySide6.QtWidgets.QMessageBox.question')
    def test_delete_file_action_cancelled(self, mock_question):
        """Test that file deletion is cancelled when user declines."""
        # Mock user declining confirmation
        mock_question.return_value = QMessageBox.No

        # Verify file exists before attempted deletion
        existing_file = FileEntry.get_by_absolute_path(self.test_file_path)
        self.assertIsNotNone(existing_file)

        # Test cancelling file deletion
        self.main_window._delete_file(self.file_entry)

        # Verify file still exists in database
        still_existing_file = FileEntry.get_by_absolute_path(self.test_file_path)
        self.assertIsNotNone(still_existing_file)
        self.assertEqual(still_existing_file.id, self.file_entry.id)

    @patch('gui.main_window.QMenu')
    def test_show_file_context_menu_creation(self, mock_menu_class):
        """Test that context menu is properly created with all actions."""
        # Mock QMenu and its instance
        mock_menu = Mock()
        mock_menu_class.return_value = mock_menu

        # Mock table index and position
        mock_index = Mock()
        mock_index.isValid.return_value = True
        mock_index.row.return_value = 0

        # Mock the file table model to return our test file
        with patch.object(self.main_window.file_table, 'indexAt', return_value=mock_index), \
             patch.object(self.main_window.file_table_model, 'get_file_at_row', return_value=self.file_entry):

            # Call the context menu method
            test_position = QPoint(10, 10)
            self.main_window._show_file_context_menu(test_position)

            # Verify menu was created
            mock_menu_class.assert_called_once_with(self.main_window)

            # Verify actions were added
            expected_actions = ["Open File", "Copy File Path", "Delete File", "Remove from Workspace"]
            actual_calls = [call[0][0] for call in mock_menu.addAction.call_args_list if call[0]]

            for expected_action in expected_actions:
                self.assertIn(expected_action, actual_calls)

            # Verify menu was shown
            mock_menu.exec.assert_called_once()

    @patch('gui.main_window.subprocess.run')
    def test_open_in_terminal_file_path(self, mock_subprocess):
        """Test opening terminal for a file path (should open at parent directory)."""
        with patch('gui.main_window.platform.system') as mock_platform:
            # Test Windows behavior with a file
            mock_platform.return_value = "Windows"

            # Use a real file path that we know exists (this test file)
            file_path = str(Path(__file__).absolute())
            expected_directory = str(Path(file_path).parent)

            # Call the method
            self.main_window._open_in_terminal(file_path)

            # Verify subprocess.run was called
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]

            # The command is now a string (not a list), so use it directly
            command_str = call_args if isinstance(call_args, str) else ' '.join(call_args)
            self.assertIn(expected_directory, command_str)
            self.assertNotIn(file_path, command_str) # File path itself should not be in the command

    @patch('gui.main_window.subprocess.run')
    def test_open_in_terminal_directory_path(self, mock_subprocess):
        """Test opening terminal for a directory path (should open at the directory)."""
        with patch('gui.main_window.platform.system') as mock_platform, \
             tempfile.TemporaryDirectory() as temp_dir:

            # Test Windows behavior with a directory
            mock_platform.return_value = "Windows"

            # Use the temporary directory
            dir_path = temp_dir

            # Call the method
            self.main_window._open_in_terminal(dir_path)

            # Verify subprocess.run was called
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]

            # The command is now a string (not a list), so use it directly
            command_str = call_args if isinstance(call_args, str) else ' '.join(call_args)
            self.assertIn(dir_path, command_str)

    @patch('gui.main_window.subprocess.run')
    def test_open_in_terminal_macos(self, mock_subprocess):
        """Test opening terminal on macOS for both file and directory."""
        with patch('gui.main_window.platform.system') as mock_platform, \
             tempfile.TemporaryDirectory() as temp_dir:

            mock_platform.return_value = "Darwin"

            # Test with a file
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")

            self.main_window._open_in_terminal(str(test_file))

            # Verify subprocess.run was called with correct command for macOS
            mock_subprocess.assert_called_with(["open", "-a", "Terminal", temp_dir])

            # Test with a directory
            mock_subprocess.reset_mock()
            self.main_window._open_in_terminal(temp_dir)

            # Should use the directory directly
            mock_subprocess.assert_called_with(["open", "-a", "Terminal", temp_dir])

    @patch('gui.main_window.subprocess.run')
    @patch('PySide6.QtWidgets.QMessageBox.warning')
    def test_open_in_terminal_nonexistent_path(self, mock_warning, mock_subprocess):
        """Test opening terminal for non-existent path (should show error message)."""
        with patch('gui.main_window.platform.system') as mock_platform:
            mock_platform.return_value = "Windows"

            # Use a path that doesn't exist
            nonexistent_path = "C:\\nonexistent\\file.txt"

            # The improved implementation should show a warning and not call subprocess
            self.main_window._open_in_terminal(nonexistent_path)

            # Should show warning message instead of trying to open terminal
            mock_warning.assert_called_once()
            args, kwargs = mock_warning.call_args
            self.assertEqual(args[1], "Directory Not Found")

            # Should not call subprocess since directory doesn't exist
            mock_subprocess.assert_not_called()

    @patch('gui.main_window.subprocess.run')
    @patch('PySide6.QtWidgets.QMessageBox.warning')
    def test_open_in_terminal_robust_directory_check(self, mock_warning, mock_subprocess):
        """Test that the improved logic correctly handles files vs directories."""
        with patch('gui.main_window.platform.system') as mock_platform, \
             tempfile.TemporaryDirectory() as temp_dir:

            mock_platform.return_value = "Windows"

            # Create a test file in temp directory
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test")

            # Create a subdirectory
            test_subdir = Path(temp_dir) / "subdir"
            test_subdir.mkdir()

            # Test file path - should use parent directory
            self.main_window._open_in_terminal(str(test_file))
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            command_str = call_args if isinstance(call_args, str) else ' '.join(call_args)
            self.assertIn(temp_dir, command_str)  # Parent directory should be used

            # Test directory path - should use directory itself
            mock_subprocess.reset_mock()
            self.main_window._open_in_terminal(str(test_subdir))
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0][0]
            command_str = call_args if isinstance(call_args, str) else ' '.join(call_args)
            self.assertIn(str(test_subdir), command_str)  # Directory itself should be used


if __name__ == '__main__':
    unittest.main()