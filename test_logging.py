#!/usr/bin/env python3
"""
Test script to verify comprehensive logging functionality.

This script tests logging in core modules: scanner, models, and watcher.
"""

import os
import tempfile
import shutil
from pathlib import Path
from core.logging_config import setup_logging
from core.models import Workspace, Tag
from core.scanner import FileEntry, FilesystemScanner
from core.watcher import FilesystemWatcher

def test_logging():
    """Test logging functionality across core modules."""

    # Setup logging to INFO level to see log output
    logger = setup_logging(level="INFO")
    print("=== Testing Comprehensive Logging ===\n")

    # Test 1: Workspace operations (models.py logging)
    print("1. Testing Workspace operations logging:")
    try:
        workspace = Workspace.create("Test Logging Workspace")
        print(f"   Created workspace: {workspace.name} (ID: {workspace.id})")

        # Clean up
        Workspace.delete(workspace.id)
        print("   Deleted test workspace\n")

    except Exception as e:
        print(f"   Error in workspace test: {e}\n")

    # Test 2: File scanning operations (scanner.py logging)
    print("2. Testing File scanning operations logging:")
    try:
        # Create test workspace and files
        test_workspace = Workspace.create("Scanner Test Workspace")

        # Create temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "test1.py").write_text("# Test file 1")
            (temp_path / "test2.txt").write_text("Test file 2")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "test3.md").write_text("# Test file 3")

            # Test FileEntry.create (individual)
            file_entry = FileEntry.create(
                workspace_id=test_workspace.id,
                relative_path="test_log.py",
                absolute_path=str(temp_path / "test1.py"),
                file_type="py"
            )
            print(f"   Created file entry: {file_entry.relative_path}")

            # Test batch creation
            batch_files = [
                {
                    'workspace_id': test_workspace.id,
                    'relative_path': 'batch_test1.txt',
                    'absolute_path': str(temp_path / "test2.txt"),
                    'file_type': 'txt'
                },
                {
                    'workspace_id': test_workspace.id,
                    'relative_path': 'batch_test2.md',
                    'absolute_path': str(temp_path / "subdir" / "test3.md"),
                    'file_type': 'md'
                }
            ]

            batch_entries = FileEntry.create_batch(batch_files)
            print(f"   Created {len(batch_entries)} entries via batch operation")

            # Test search operations
            search_results = FileEntry.search_by_keyword("test", test_workspace.id)
            print(f"   Search by keyword returned {len(search_results)} results")

        # Clean up
        Workspace.delete(test_workspace.id)
        print("   Cleaned up scanner test workspace\n")

    except Exception as e:
        print(f"   Error in scanner test: {e}\n")

    # Test 3: Tag operations (models.py logging)
    print("3. Testing Tag operations logging:")
    try:
        # Create test workspace and file
        tag_workspace = Workspace.create("Tag Test Workspace")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "tag_test.py"
            temp_file.write_text("# Test file for tagging")

            # Create file entry
            file_entry = FileEntry.create(
                workspace_id=tag_workspace.id,
                relative_path="tag_test.py",
                absolute_path=str(temp_file),
                file_type="py"
            )

            # Test tag operations
            tag1 = Tag.add_tag_to_file(file_entry.id, "test-tag")
            print(f"   Added tag: {tag1.tag_name}")

            tag2 = Tag.add_tag_to_file(file_entry.id, "python")
            print(f"   Added tag: {tag2.tag_name}")

            # Test search by tags
            tagged_files = FileEntry.search_by_tags(["test"], tag_workspace.id)
            print(f"   Search by tags returned {len(tagged_files)} results")

        # Clean up
        Workspace.delete(tag_workspace.id)
        print("   Cleaned up tag test workspace\n")

    except Exception as e:
        print(f"   Error in tag test: {e}\n")

    # Test 4: Watcher operations (watcher.py logging)
    print("4. Testing Watcher operations logging:")
    try:
        watcher_workspace = Workspace.create("Watcher Test Workspace")

        with tempfile.TemporaryDirectory() as temp_dir:
            from core.models import WorkspacePath

            # Add path to workspace
            workspace_path = WorkspacePath.add_path(
                workspace_id=watcher_workspace.id,
                root_path=temp_dir,
                path_type='folder'
            )

            # Test watcher startup
            watcher = FilesystemWatcher()
            success = watcher.start_watching_workspace(watcher_workspace.id)
            print(f"   Started watching workspace: {success}")

            if success:
                watcher.stop_watching_workspace(watcher_workspace.id)
                print("   Stopped watching workspace")

        # Clean up
        Workspace.delete(watcher_workspace.id)
        print("   Cleaned up watcher test workspace\n")

    except Exception as e:
        print(f"   Error in watcher test: {e}\n")

    print("=== Logging Test Complete ===")
    print("\nCheck the console output above for log messages from each component.")
    print("You should see INFO and DEBUG level messages throughout the test.")

if __name__ == "__main__":
    test_logging()