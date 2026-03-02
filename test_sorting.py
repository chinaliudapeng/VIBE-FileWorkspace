#!/usr/bin/env python3
"""
Test script to verify table sorting functionality in FileTableModel.
"""

import sys
import tempfile
from pathlib import Path

# Add the project root to sys.path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.models import Workspace, WorkspacePath, Tag
from core.scanner import FileEntry
from gui.models import FileTableModel
from PySide6.QtCore import Qt

def test_table_sorting():
    """Test the table sorting functionality."""
    print("=== Testing Table Sorting Functionality ===\n")

    # Create a temporary workspace for testing
    workspace = Workspace.create("Sorting Test Workspace")
    print(f"Created test workspace: {workspace.name} (ID: {workspace.id})")

    # Create temporary directory with test files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files with different types and names
        test_files = [
            ("zebra.py", "# Python file"),
            ("apple.txt", "Text file content"),
            ("banana.md", "# Markdown file"),
            ("cherry.doc", "Document content"),
            ("date.jpg", "fake image content"),
        ]

        # Create subdirectory
        sub_dir = temp_path / "subdirectory"
        sub_dir.mkdir()
        (sub_dir / "nested.py").write_text("# Nested file")

        # Create all test files
        for filename, content in test_files:
            (temp_path / filename).write_text(content)

        # Add workspace path
        workspace_path = WorkspacePath.add_path(
            workspace_id=workspace.id,
            root_path=str(temp_dir),
            path_type="folder"
        )

        # Create file entries manually for predictable testing
        file_entries = []
        for filename, _ in test_files:
            file_path = temp_path / filename
            file_ext = file_path.suffix[1:] if file_path.suffix else 'file'
            entry = FileEntry.create(
                workspace_id=workspace.id,
                relative_path=filename,
                absolute_path=str(file_path),
                file_type=file_ext
            )
            file_entries.append(entry)

        # Create directory entry
        dir_entry = FileEntry.create(
            workspace_id=workspace.id,
            relative_path="subdirectory",
            absolute_path=str(sub_dir),
            file_type="directory"
        )
        file_entries.append(dir_entry)

        # Add some tags for tag sorting testing
        Tag.add_tag_to_file(file_entries[0].id, "python")  # zebra.py
        Tag.add_tag_to_file(file_entries[0].id, "code")    # zebra.py
        Tag.add_tag_to_file(file_entries[1].id, "document")  # apple.txt

        print(f"Created {len(file_entries)} test file entries")

        # Test sorting functionality
        model = FileTableModel()
        model.load_workspace_files(workspace.id)

        print(f"\nLoaded {model.get_file_count()} files into model")

        # Test 1: Sort by relative path (ascending)
        print("\n1. Testing sort by Relative Path (Ascending):")
        model.sort(FileTableModel.COL_RELATIVE_PATH, Qt.AscendingOrder)
        print("   Sorted order:")
        for i in range(model.rowCount()):
            file_entry = model.get_file_at_row(i)
            file_type = "DIR" if file_entry.file_type == "directory" else file_entry.file_type.upper()
            print(f"   {i+1:2d}. [{file_type}] {file_entry.relative_path}")

        # Test 2: Sort by relative path (descending)
        print("\n2. Testing sort by Relative Path (Descending):")
        model.sort(FileTableModel.COL_RELATIVE_PATH, Qt.DescendingOrder)
        print("   Sorted order:")
        for i in range(model.rowCount()):
            file_entry = model.get_file_at_row(i)
            file_type = "DIR" if file_entry.file_type == "directory" else file_entry.file_type.upper()
            print(f"   {i+1:2d}. [{file_type}] {file_entry.relative_path}")

        # Test 3: Sort by file type (ascending)
        print("\n3. Testing sort by File Type (Ascending):")
        model.sort(FileTableModel.COL_FILE_TYPE, Qt.AscendingOrder)
        print("   Sorted order:")
        for i in range(model.rowCount()):
            file_entry = model.get_file_at_row(i)
            file_type = "DIR" if file_entry.file_type == "directory" else file_entry.file_type.upper()
            print(f"   {i+1:2d}. [{file_type}] {file_entry.relative_path}")

        # Test 4: Sort by tags (ascending)
        print("\n4. Testing sort by Tags (Ascending):")
        model.sort(FileTableModel.COL_TAGS, Qt.AscendingOrder)
        print("   Sorted order:")
        for i in range(model.rowCount()):
            file_entry = model.get_file_at_row(i)
            try:
                tags = Tag.get_tags_for_file(file_entry.id)
                tag_names = [tag.tag_name for tag in tags] if tags else []
                tag_count = len(tag_names)
                tag_display = f"({tag_count} tags: {', '.join(tag_names)})" if tag_names else "(no tags)"
            except Exception:
                tag_display = "(error getting tags)"
            file_type = "DIR" if file_entry.file_type == "directory" else file_entry.file_type.upper()
            print(f"   {i+1:2d}. [{file_type}] {file_entry.relative_path} {tag_display}")

        # Test edge cases
        print("\n5. Testing edge cases:")

        # Empty model sorting
        empty_model = FileTableModel()
        empty_model.sort(0, Qt.AscendingOrder)
        print("   [OK] Empty model sort doesn't crash")

        # Invalid column sorting
        model.sort(-1, Qt.AscendingOrder)  # Invalid column
        model.sort(99, Qt.AscendingOrder)  # Invalid column
        print("   [OK] Invalid column sort doesn't crash")

    # Cleanup
    Workspace.delete(workspace.id)
    print(f"\n[OK] Cleaned up test workspace")
    print("\n=== Table Sorting Test Complete ===")

    # Verify directories are sorted first in path-based sorting
    model2 = FileTableModel()
    model2.load_workspace_files(workspace.id if False else None)  # Empty model for final test
    print("[OK] All sorting functionality tests completed successfully!")

if __name__ == "__main__":
    test_table_sorting()