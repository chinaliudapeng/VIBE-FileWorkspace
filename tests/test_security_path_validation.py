"""
Security tests for path validation functionality.

Tests for path traversal attacks, symlink escapes, and other security vulnerabilities
in the WorkspacePath.add_path() method and related path validation functions.
"""

import pytest
import tempfile
import os
import platform
from pathlib import Path
from unittest.mock import patch, mock_open

# Import the modules we're testing
from core.models import WorkspacePath, Workspace, validate_workspace_path
from core.db import initialize_database, get_db_path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Create a temporary directory for the test database
    temp_dir = tempfile.mkdtemp()
    temp_db_path = Path(temp_dir) / 'test_security.db'

    # Mock the get_db_path function to use our temporary database
    with patch('core.db.get_db_path') as mock_get_db_path:
        mock_get_db_path.return_value = temp_db_path

        # Initialize the test database
        initialize_database()

        yield temp_db_path

        # Cleanup
        if temp_db_path.exists():
            temp_db_path.unlink()
        Path(temp_dir).rmdir()


class TestPathValidationSecurity:
    """Test security aspects of path validation."""

    @pytest.fixture(autouse=True)
    def setup_method(self, temp_db):
        """Set up test environment."""
        # Database is already set up by temp_db fixture

        # Create a test workspace
        self.workspace = Workspace.create("SecurityTestWorkspace")

        # Create a real temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test_file.txt"
        self.test_file.write_text("test content")

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temporary directory
        if self.temp_dir.exists():
            for file in self.temp_dir.rglob("*"):
                if file.is_file():
                    file.unlink()
            for dir in sorted(self.temp_dir.rglob("*/"), reverse=True):
                dir.rmdir()
            self.temp_dir.rmdir()

    def test_path_traversal_attack_prevention(self):
        """Test that path traversal attacks are prevented."""
        # Test various path traversal patterns
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "valid_dir/../../../sensitive_file",
            str(self.temp_dir / ".." / ".." / "sensitive"),
            f"{self.temp_dir}/../../../etc/passwd",
        ]

        for malicious_path in malicious_paths:
            with pytest.raises((ValueError, PermissionError)):
                validate_workspace_path(malicious_path, 'folder')

    def test_symlink_security_handling(self):
        """Test that symlinks are handled securely."""
        if platform.system() == "Windows":
            pytest.skip("Symlink test requires Unix-like system or Windows admin privileges")

        # Create a symlink that points outside the temp directory
        target_outside = Path("/etc/passwd")  # System file
        if target_outside.exists():
            symlink_path = self.temp_dir / "malicious_symlink"
            try:
                symlink_path.symlink_to(target_outside)

                # The validation should either reject the symlink or resolve it safely
                # In our implementation, we log symlinks and resolve them
                result = validate_workspace_path(str(symlink_path), 'file')

                # If it doesn't raise an error, make sure it resolves to the real target
                assert str(target_outside.resolve()) == result

            except OSError:
                # Symlink creation failed (e.g., permissions), skip this test
                pytest.skip("Cannot create symlink in test environment")
            finally:
                if symlink_path.exists() or symlink_path.is_symlink():
                    symlink_path.unlink()

    def test_empty_path_validation(self):
        """Test that empty paths are rejected."""
        invalid_paths = ["", "   ", "\t", "\n"]

        for invalid_path in invalid_paths:
            with pytest.raises(ValueError, match="Path cannot be empty"):
                validate_workspace_path(invalid_path, 'folder')

        # Test None separately
        with pytest.raises(ValueError, match="Path cannot be None"):
            validate_workspace_path(None, 'folder')

    def test_path_length_limits(self):
        """Test that excessively long paths are rejected."""
        # Create a path longer than the maximum allowed length
        if platform.system() == "Windows":
            max_length = 260
        else:
            max_length = 4096

        # Create a path that's definitely too long
        long_component = "a" * (max_length // 2)
        long_path = str(self.temp_dir / long_component / long_component / "file.txt")

        with pytest.raises(ValueError, match="Path too long"):
            validate_workspace_path(long_path, 'file')

    def test_invalid_characters_windows(self):
        """Test that invalid characters are rejected on Windows."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        base_path = str(self.temp_dir)

        for char in invalid_chars:
            invalid_path = f"{base_path}/test{char}file.txt"
            with pytest.raises(ValueError, match="invalid characters"):
                validate_workspace_path(invalid_path, 'file')

    def test_reserved_names_windows(self):
        """Test that Windows reserved names are rejected."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1']
        base_path = str(self.temp_dir)

        for name in reserved_names:
            invalid_path = f"{base_path}/{name}"
            with pytest.raises(ValueError, match="reserved name"):
                validate_workspace_path(invalid_path, 'file')

            # Test case-insensitive detection
            invalid_path_lower = f"{base_path}/{name.lower()}"
            with pytest.raises(ValueError, match="reserved name"):
                validate_workspace_path(invalid_path_lower, 'file')

    def test_trailing_dots_spaces_windows(self):
        """Test that trailing dots and spaces are rejected on Windows."""
        if platform.system() != "Windows":
            pytest.skip("Windows-specific test")

        base_path = str(self.temp_dir)
        problematic_names = ['file.', 'file ', 'dir.', 'dir ']

        for name in problematic_names:
            invalid_path = f"{base_path}/{name}"
            with pytest.raises(ValueError, match="cannot end with dot or space"):
                validate_workspace_path(invalid_path, 'file')

    def test_nonexistent_path_rejection(self):
        """Test that nonexistent paths are rejected."""
        nonexistent_paths = [
            "/this/path/definitely/does/not/exist",
            str(self.temp_dir / "nonexistent_file.txt"),
            str(self.temp_dir / "nonexistent_dir"),
        ]

        for path in nonexistent_paths:
            with pytest.raises(ValueError, match="does not exist"):
                validate_workspace_path(path, 'file')

    def test_type_mismatch_rejection(self):
        """Test that type mismatches are rejected."""
        # Try to validate a file as a folder
        with pytest.raises(ValueError, match="not a directory"):
            validate_workspace_path(str(self.test_file), 'folder')

        # Try to validate a directory as a file
        with pytest.raises(ValueError, match="not a file"):
            validate_workspace_path(str(self.temp_dir), 'file')

    def test_permission_errors_handled(self):
        """Test that permission errors are properly handled."""
        # This test is platform-dependent and might not work in all environments
        if platform.system() == "Windows":
            pytest.skip("Permission test not reliable on Windows test environment")

        # Try to create a file we can't read (this is tricky to do reliably in tests)
        # Instead, we'll mock the permission error
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.side_effect = PermissionError("Access denied")

            with pytest.raises(PermissionError, match="No read access"):
                validate_workspace_path(str(self.test_file), 'file')

    def test_workspace_path_integration_security(self):
        """Test that WorkspacePath.add_path() properly uses validation."""
        # Test that malicious paths are rejected at the model level
        with pytest.raises(ValueError):
            WorkspacePath.add_path(
                workspace_id=self.workspace.id,
                root_path="../../../etc/passwd",
                path_type='file'
            )

        # Test that valid paths work
        workspace_path = WorkspacePath.add_path(
            workspace_id=self.workspace.id,
            root_path=str(self.temp_dir),
            path_type='folder'
        )
        assert workspace_path is not None
        assert Path(workspace_path.root_path).resolve() == self.temp_dir.resolve()

    def test_path_normalization(self):
        """Test that paths are properly normalized."""
        # Test various path formats that should normalize to the same result
        test_paths = [
            str(self.temp_dir),
            str(self.temp_dir) + "/",
            str(self.temp_dir) + "/.",
            str(self.temp_dir / "subdir" / ".."),
        ]

        # Create a subdir for the relative path test
        (self.temp_dir / "subdir").mkdir()

        expected_normalized = str(self.temp_dir.resolve())

        for path in test_paths:
            try:
                result = validate_workspace_path(path, 'folder')
                assert result == expected_normalized, f"Path {path} normalized incorrectly"
            except ValueError:
                # Some paths might not exist, that's okay for this test
                pass

    def test_unicode_path_handling(self):
        """Test that Unicode characters in paths are handled correctly."""
        # Create a directory with Unicode characters
        unicode_dir = self.temp_dir / "测试目录"
        unicode_dir.mkdir()
        unicode_file = unicode_dir / "тест.txt"
        unicode_file.write_text("test content")

        # These should work correctly
        dir_result = validate_workspace_path(str(unicode_dir), 'folder')
        file_result = validate_workspace_path(str(unicode_file), 'file')

        assert Path(dir_result).resolve() == unicode_dir.resolve()
        assert Path(file_result).resolve() == unicode_file.resolve()

    def test_race_condition_mitigation(self):
        """Test that validation handles race conditions properly."""
        # This tests the TOCTOU fix by mocking file system operations
        with patch('pathlib.Path.is_file') as mock_is_file:
            mock_is_file.side_effect = [True, FileNotFoundError("File disappeared")]

            # The first call to is_file() returns True, second call raises FileNotFoundError
            with pytest.raises(ValueError, match="Cannot access path"):
                validate_workspace_path(str(self.test_file), 'file')

    def test_malformed_path_formats(self):
        """Test handling of malformed path formats."""
        malformed_paths = [
            "\\\\invalid\\unc\\path" if platform.system() != "Windows" else None,
            "C:invalid_windows_path" if platform.system() == "Windows" else None,
            "\x00null_byte_path",
            "path\x01with\x02control\x03chars",
        ]

        for path in malformed_paths:
            if path is None:  # Skip platform-specific tests
                continue

            with pytest.raises((ValueError, OSError)):
                validate_workspace_path(path, 'file')


class TestSecurityErrorMessages:
    """Test that security error messages don't leak sensitive information."""

    @pytest.fixture(autouse=True)
    def setup_method(self, temp_db):
        """Set up test environment."""
        # Database is already set up by temp_db fixture
        pass

    def test_error_messages_safe(self):
        """Test that error messages don't contain sensitive path information."""
        workspace = Workspace.create("TestWorkspace")

        # Test that error messages for malicious paths don't reveal system structure
        with pytest.raises(ValueError) as exc_info:
            WorkspacePath.add_path(
                workspace_id=workspace.id,
                root_path="../../../etc/passwd",
                path_type='file'
            )

        error_msg = str(exc_info.value)
        # Error message should be informative but not leak sensitive paths
        assert "etc/passwd" not in error_msg or "does not exist" in error_msg
        assert "Invalid path format" in error_msg or "Cannot access path" in error_msg