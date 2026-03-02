"""Tests for hiding rules regex pattern validation."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from PySide6.QtWidgets import QApplication, QMessageBox

# Import modules under test
from core.models import validate_regex_patterns, Workspace, WorkspacePath
from gui.dialogs import HidingRulesPillWidget
from core.db import initialize_database


class TestHidingRulesValidation(unittest.TestCase):
    """Test cases for hiding rules regex validation."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Create QApplication instance (required for GUI components)
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """Set up test database."""
        # Create temporary database for testing
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / 'test_hiding_rules.db'

        # Patch get_db_path to use our test database
        self.db_patcher = patch('core.db.get_db_path')
        self.mock_get_db_path = self.db_patcher.start()
        self.mock_get_db_path.return_value = self.db_path

        # Initialize test database
        initialize_database()

        # Create test workspace
        self.workspace = Workspace.create("Test Workspace")

    def tearDown(self):
        """Clean up test environment."""
        self.db_patcher.stop()
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.temp_dir).rmdir()

    def test_validate_regex_patterns_valid_patterns(self):
        """Test that valid regex patterns pass validation."""
        valid_patterns = [
            "",  # Empty string should be valid
            "   ",  # Whitespace only should be valid
            ".*\\.tmp$",  # Files ending with .tmp
            "node_modules",  # Simple string
            "__pycache__",  # Another simple string
            ".*\\.(log|tmp)$",  # Files ending with .log or .tmp
            "test.*\\.py;.*\\.pyc$",  # Multiple patterns separated by semicolon
        ]

        for pattern in valid_patterns:
            with self.subTest(pattern=pattern):
                # Should not raise any exception
                validate_regex_patterns(pattern)

    def test_validate_regex_patterns_invalid_patterns(self):
        """Test that invalid regex patterns raise ValueError."""
        invalid_patterns = [
            "[",  # Unclosed character class
            "(?P<incomplete",  # Incomplete named group
            "*",  # Invalid quantifier
            "(?P<>test)",  # Empty group name
            "\\",  # Incomplete escape sequence
            "valid_pattern;[invalid",  # Mix of valid and invalid patterns
        ]

        for pattern in invalid_patterns:
            with self.subTest(pattern=pattern):
                with self.assertRaises(ValueError) as cm:
                    validate_regex_patterns(pattern)
                # Error message should mention the invalid pattern
                self.assertIn("Invalid regex", str(cm.exception))

    def test_add_path_with_invalid_hiding_rules_fails(self):
        """Test that adding a path with invalid hiding rules fails."""
        invalid_rule = "[unclosed_bracket"

        with self.assertRaises(ValueError) as cm:
            WorkspacePath.add_path(
                workspace_id=self.workspace.id,
                root_path="/test/path",
                path_type="folder",
                hiding_rules=invalid_rule
            )

        # Error should mention invalid regex
        self.assertIn("Invalid regex", str(cm.exception))
        self.assertIn(invalid_rule, str(cm.exception))

    def test_add_path_with_valid_hiding_rules_succeeds(self):
        """Test that adding a path with valid hiding rules succeeds."""
        valid_rules = ".*\\.tmp$;__pycache__"

        # Should not raise any exception
        workspace_path = WorkspacePath.add_path(
            workspace_id=self.workspace.id,
            root_path="/test/path",
            path_type="folder",
            hiding_rules=valid_rules
        )

        self.assertEqual(workspace_path.hiding_rules, valid_rules)

    def test_update_hiding_rules_with_invalid_patterns_fails(self):
        """Test that updating hiding rules with invalid patterns fails."""
        # First create a path with valid rules
        workspace_path = WorkspacePath.add_path(
            workspace_id=self.workspace.id,
            root_path="/test/path",
            path_type="folder",
            hiding_rules="valid_pattern"
        )

        # Try to update with invalid rules
        invalid_rule = "*invalid"
        with self.assertRaises(ValueError) as cm:
            WorkspacePath.update_hiding_rules(workspace_path.id, invalid_rule)

        # Error should mention invalid regex
        self.assertIn("Invalid regex", str(cm.exception))

    def test_update_hiding_rules_with_valid_patterns_succeeds(self):
        """Test that updating hiding rules with valid patterns succeeds."""
        # First create a path
        workspace_path = WorkspacePath.add_path(
            workspace_id=self.workspace.id,
            root_path="/test/path",
            path_type="folder",
            hiding_rules="old_pattern"
        )

        # Update with valid rules
        new_rules = ".*\\.log$;.*\\.tmp$"
        success = WorkspacePath.update_hiding_rules(workspace_path.id, new_rules)

        self.assertTrue(success)

        # Verify the rules were updated
        updated_path = WorkspacePath.get_by_id(workspace_path.id)
        self.assertEqual(updated_path.hiding_rules, new_rules)

    def test_gui_parse_hiding_rules_with_invalid_patterns_raises_error(self):
        """Test that GUI parsing of invalid hiding rules raises appropriate error."""
        # Create a mock workspace path
        workspace_path = Mock()
        workspace_path.hiding_rules = "valid_pattern"

        # Create the widget
        widget = HidingRulesPillWidget(workspace_path)

        # Try to parse invalid rules
        invalid_rules = "[unclosed;(?P<incomplete"
        with self.assertRaises(ValueError) as cm:
            widget.parse_hiding_rules(invalid_rules)

        # Error message should contain information about both invalid patterns
        error_msg = str(cm.exception)
        self.assertIn("Invalid regex", error_msg)
        self.assertIn("[unclosed", error_msg)
        self.assertIn("(?P<incomplete", error_msg)

    def test_gui_parse_hiding_rules_with_valid_patterns_succeeds(self):
        """Test that GUI parsing of valid hiding rules works correctly."""
        # Create a mock workspace path
        workspace_path = Mock()
        workspace_path.hiding_rules = "valid_pattern"

        # Create the widget
        widget = HidingRulesPillWidget(workspace_path)

        # Parse valid rules
        valid_rules = ".*\\.tmp$;node_modules;__pycache__"
        parsed_rules = widget.parse_hiding_rules(valid_rules)

        expected_rules = [".*\\.tmp$", "node_modules", "__pycache__"]
        self.assertEqual(parsed_rules, expected_rules)

    def test_gui_initialization_with_invalid_existing_rules(self):
        """Test that GUI handles existing invalid rules gracefully."""
        # Create a mock workspace path with invalid rules
        workspace_path = Mock()
        workspace_path.root_path = "/test/path"
        workspace_path.hiding_rules = "[invalid_pattern"

        # Creating the widget should handle the error gracefully
        # (It should clear the invalid rules and use empty list)
        widget = HidingRulesPillWidget(workspace_path)

        # Widget should have empty rules after handling the invalid ones
        self.assertEqual(widget.hiding_rules, [])
        # The workspace path should have been cleared of invalid rules
        self.assertEqual(workspace_path.hiding_rules, "")

    def test_comprehensive_regex_patterns_validation(self):
        """Test validation of various complex but valid regex patterns."""
        complex_valid_patterns = [
            "^.*\\.(?:tmp|log|cache)$",  # Files ending with specific extensions
            "(?!.*important).*\\.txt$",  # Negative lookahead
            ".*/(node_modules|__pycache__|\\.git)/.*",  # Common ignore patterns
            ".*\\.py[co]$",  # Python compiled files
            ".*~$",  # Backup files
            "\\.DS_Store",  # macOS system files
            "Thumbs\\.db",  # Windows system files
        ]

        combined_pattern = ";".join(complex_valid_patterns)

        # Should not raise any exception
        validate_regex_patterns(combined_pattern)

        # Should also work when adding to workspace
        workspace_path = WorkspacePath.add_path(
            workspace_id=self.workspace.id,
            root_path="/complex/test",
            path_type="folder",
            hiding_rules=combined_pattern
        )

        self.assertEqual(workspace_path.hiding_rules, combined_pattern)


if __name__ == '__main__':
    unittest.main()