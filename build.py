#!/usr/bin/env python3
"""
Cross-platform build script for Workspace File Indexer using PyInstaller.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"OK {description} completed")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"ERROR {description} failed:")
        print(f"  Error: {e.stderr}")
        print(f"  Exit code: {e.returncode}")
        raise

def check_dependencies():
    """Check if all required dependencies are available."""
    print("Checking dependencies...")

    # Check PyInstaller
    try:
        output = run_command("python -m PyInstaller --version", "Checking PyInstaller")
        print(f"OK PyInstaller {output.strip()}")
    except:
        print("ERROR PyInstaller not found. Install with: pip install pyinstaller>=6.0.0")
        return False

    # Check required modules
    modules = ['PySide6', 'watchdog', 'send2trash', 'click']
    for module in modules:
        try:
            subprocess.run([sys.executable, '-c', f'import {module}'], check=True, capture_output=True)
            print(f"OK {module} available")
        except subprocess.CalledProcessError:
            print(f"ERROR {module} not available. Install with: pip install -r requirements.txt")
            return False

    return True

def build_application(name, entry_point, app_type="console"):
    """Build an application using PyInstaller."""
    print(f"\nBuilding {name}...")

    # Common arguments
    args = [
        "python", "-m", "PyInstaller",
        "--clean",
        "--onefile",
        "--distpath", "dist",
        "--workpath", "build",
        "--name", name,
    ]

    # Add data directories
    args.extend([
        "--add-data", "core:core" if platform.system() != "Windows" else "core;core",
    ])

    # App-specific arguments
    if app_type == "gui":
        if platform.system() == "Windows":
            args.append("--windowed")
        else:
            args.append("--windowed")

        args.extend([
            "--add-data", "gui:gui" if platform.system() != "Windows" else "gui;gui",
            "--hidden-import", "PySide6.QtCore",
            "--hidden-import", "PySide6.QtGui",
            "--hidden-import", "PySide6.QtWidgets",
        ])

    # Common hidden imports
    args.extend([
        "--hidden-import", "watchdog.observers",
        "--hidden-import", "watchdog.events",
        "--hidden-import", "send2trash",
        "--hidden-import", "click",
    ])

    # Add entry point
    args.append(entry_point)

    # Run PyInstaller
    try:
        run_command(" ".join(args), f"Building {name}")
        print(f"OK {name} built successfully")
        return True
    except:
        print(f"ERROR Failed to build {name}")
        return False

def test_executables():
    """Test the built executables."""
    print("\nTesting built executables...")

    dist_dir = Path("dist")

    # Test CLI
    cli_exe = dist_dir / ("WorkspaceIndexer-CLI.exe" if platform.system() == "Windows" else "WorkspaceIndexer-CLI")
    if cli_exe.exists():
        try:
            output = run_command(f'"{cli_exe}" --version', "Testing CLI executable")
            print(f"OK CLI working: {output.strip()}")
        except:
            print("ERROR CLI executable test failed")
    else:
        print("ERROR CLI executable not found")

    # Test GUI (just check if it exists)
    gui_exe = dist_dir / ("WorkspaceIndexer-GUI.exe" if platform.system() == "Windows" else "WorkspaceIndexer-GUI")
    if gui_exe.exists():
        print("OK GUI executable created (manual testing required)")
    else:
        print("ERROR GUI executable not found")

def main():
    """Main build process."""
    print("=== Workspace File Indexer Build Script ===")
    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version}")
    print()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Clean previous builds
    print("\nCleaning previous builds...")
    for dir_name in ["build", "dist"]:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"OK Removed {dir_name}")

    # Create output directory
    os.makedirs("dist", exist_ok=True)

    # Build applications
    success = True

    # Build GUI
    if not build_application("WorkspaceIndexer-GUI", "launch_gui.py", "gui"):
        success = False

    # Build CLI
    if not build_application("WorkspaceIndexer-CLI", "cli/main.py", "console"):
        success = False

    if not success:
        print("\nERROR Some builds failed")
        sys.exit(1)

    # Test executables
    test_executables()

    # Display results
    print(f"\n=== Build Complete ===")
    print(f"Output directory: dist/")

    dist_dir = Path("dist")
    for file in dist_dir.glob("*"):
        if file.is_file():
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"  {file.name}: {size_mb:.1f} MB")

    print(f"\nTo test the applications:")
    print(f"  GUI: dist/WorkspaceIndexer-GUI{'exe' if platform.system() == 'Windows' else ''}")
    print(f"  CLI: dist/WorkspaceIndexer-CLI{'exe' if platform.system() == 'Windows' else ''} --help")

if __name__ == "__main__":
    main()