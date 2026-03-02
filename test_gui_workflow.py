#!/usr/bin/env python3
"""
Test script to reproduce GUI workspace creation workflow.
This simulates the exact flow that happens when a user creates a workspace through the GUI.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add the project root to sys.path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.models import Workspace, WorkspacePath
from core.scanner import FileEntry, scan_workspace
from gui.models import FileTableModel
from PySide6.QtCore import QCoreApplication

def test_gui_workspace_creation_workflow():
    """Test the complete GUI workspace creation workflow."""
    print("=== Testing GUI Workspace Creation Workflow ===")

    # Initialize Qt application context
    app = QCoreApplication([])

    # Step 1: Create test directory with files (like user would select)
    print("\n1. Creating test directory with files...")
    test_dir = tempfile.mkdtemp(prefix="gui_test_workspace_")
    print(f"Test directory: {test_dir}")

    # Create various test files
    test_files = [
        "main.py",
        "config.json",
        "README.md",
        "src/app.py",
        "src/utils.py",
        "data/input.txt",
        "data/output.csv"
    ]

    for file_path in test_files:
        full_path = Path(test_dir) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(f"Content of {file_path}")

    print(f"Created {len(test_files)} test files")

    # Step 2: Simulate workspace dialog creation (WorkspaceDialog.save_workspace)
    print("\n2. Creating workspace through dialog simulation...")
    workspace_name = "GUI Test Workspace"

    # Create workspace (equivalent to WorkspaceDialog.save_workspace)
    workspace = Workspace.create(workspace_name)
    print(f"Created workspace: ID={workspace.id}, Name='{workspace.name}'")

    # Add path to workspace (equivalent to adding paths in dialog)
    workspace_path = WorkspacePath.add_path(
        workspace_id=workspace.id,
        root_path=test_dir,
        path_type="folder"
    )
    print(f"Added path to workspace: {workspace_path.root_path}")

    # Step 3: Simulate MainWindow._on_new_workspace post-dialog handling
    print("\n3. Simulating post-creation workflow (MainWindow._on_new_workspace)...")

    print("  3a. Scanning workspace for files...")
    files_added = scan_workspace(workspace.id)
    print(f"  Scan complete. Added {files_added} files.")

    # Step 4: Check if files are available for the file table model
    print("\n4. Testing file table model loading...")

    print("  4a. Getting files from database...")
    db_files = FileEntry.get_files_for_workspace(workspace.id)
    print(f"  Database contains {len(db_files)} files for this workspace")

    for file_entry in db_files[:5]:  # Show first 5 files
        print(f"    - {file_entry.relative_path} ({file_entry.file_type})")

    # Step 5: Test FileTableModel (what the GUI uses)
    print("\n5. Testing FileTableModel (GUI component)...")

    file_table_model = FileTableModel()
    try:
        file_table_model.load_workspace_files(workspace.id)
        row_count = file_table_model.rowCount()
        print(f"  FileTableModel loaded {row_count} files")

        if row_count > 0:
            print("  Sample files in model:")
            for i in range(min(3, row_count)):
                file_entry = file_table_model.get_file_at_row(i)
                if file_entry:
                    print(f"    - {file_entry.relative_path}")
        else:
            print("  ❌ No files loaded into FileTableModel!")

    except Exception as e:
        print(f"  ❌ Error loading files into FileTableModel: {e}")
        import traceback
        traceback.print_exc()

    # Step 6: Verify overall workflow success
    print("\n6. Workflow verification...")

    if files_added > 0 and len(db_files) > 0:
        if file_table_model.rowCount() > 0:
            print("✅ GUI workflow successful: Files created, scanned, and loaded into GUI model")
        else:
            print("❌ Issue found: Files scanned but not loaded into GUI model")
    else:
        print("❌ Issue found: Files not properly scanned into database")

    # Cleanup
    print("\n7. Cleanup...")
    try:
        Workspace.delete(workspace.id)
        import shutil
        shutil.rmtree(test_dir)
        print("Cleaned up test workspace and directory")
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == "__main__":
    test_gui_workspace_creation_workflow()