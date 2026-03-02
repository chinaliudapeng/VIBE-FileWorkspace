#!/usr/bin/env python3
"""
Test script to reproduce workspace deletion issue in GUI context.
This simulates the exact deletion flow that the GUI uses.
"""

import sys
from pathlib import Path
import tempfile
import os

# Add the project root to sys.path so we can import modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.models import Workspace, WorkspacePath
from core.scanner import scan_workspace
from core.watcher import get_global_watcher

def test_workspace_deletion():
    """Test workspace creation and deletion flow matching GUI behavior."""
    print("=== Testing Workspace Deletion Flow ===")

    # Step 1: Create a workspace (like GUI would)
    print("\n1. Creating test workspace...")
    workspace = Workspace.create("Test Workspace For Deletion Bug")
    print(f"Created workspace: ID={workspace.id}, Name='{workspace.name}'")

    # Step 2: Add a path to the workspace (like GUI workspace dialog would)
    print("\n2. Adding path to workspace...")
    test_dir = tempfile.mkdtemp(prefix="test_workspace_")
    print(f"Test directory: {test_dir}")

    # Create some test files
    (Path(test_dir) / "test1.txt").write_text("test content 1")
    (Path(test_dir) / "test2.py").write_text("print('hello world')")

    # Add the path to workspace
    workspace_path = WorkspacePath.add_path(
        workspace_id=workspace.id,
        root_path=test_dir,
        path_type="folder"
    )
    print(f"Added path: ID={workspace_path.id}, Path='{workspace_path.root_path}'")

    # Step 3: Scan the workspace (like GUI would after adding paths)
    print("\n3. Scanning workspace files...")
    scan_result = scan_workspace(workspace.id)
    print(f"Scan result: {scan_result}")

    # Step 4: Start watching the workspace (like GUI would)
    print("\n4. Starting filesystem watcher...")
    watcher = get_global_watcher()
    try:
        watch_result = watcher.start_watching_workspace(workspace.id)
        print(f"Watching started: {watch_result}")
        print(f"Is watching workspace {workspace.id}: {watcher.is_watching_workspace(workspace.id)}")
    except Exception as e:
        print(f"Error starting watcher: {e}")

    # Step 5: Try to delete the workspace (like GUI delete would)
    print("\n5. Attempting to delete workspace (GUI flow)...")
    try:
        # Stop watching first (like GUI does)
        if watcher.is_watching_workspace(workspace.id):
            stop_result = watcher.stop_watching_workspace(workspace.id)
            print(f"Stopped watching: {stop_result}")

        # Delete workspace
        delete_result = Workspace.delete(workspace.id)
        print(f"Delete result: {delete_result}")

        # Verify deletion
        remaining_workspaces = Workspace.list_all()
        print(f"Remaining workspaces: {len(remaining_workspaces)}")
        for w in remaining_workspaces:
            print(f"  - ID={w.id}, Name='{w.name}'")

        if delete_result and len(remaining_workspaces) == 0:
            print("✅ Workspace deletion successful!")
        else:
            print("❌ Workspace deletion failed!")

    except Exception as e:
        print(f"❌ Error during deletion: {e}")
        import traceback
        traceback.print_exc()

    # Cleanup
    print("\n6. Cleanup...")
    try:
        import shutil
        shutil.rmtree(test_dir)
        print("Cleaned up test directory")
    except Exception as e:
        print(f"Cleanup error: {e}")

if __name__ == "__main__":
    test_workspace_deletion()