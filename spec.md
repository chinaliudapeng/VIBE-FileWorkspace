# Specification: Workspace File Indexer

## Overview
A tool for navigating, indexing, and tagging files across multiple workspaces. Contains two components:
1. **GUI**: Built with Python and PySide6. Provides visual workspace management, fast file searching, and tagging capabilities.
2. **CLI**: Built to operate as a Skill for an AI agent, allowing headless querying and tagging using the exact same underlying database.

## Architecture
- **Language**: Python 3.x
- **GUI Framework**: PySide6
- **Database**: SQLite (Local single-file database for configuration, index, and tags)
- **Concurrency**: Background threads (QThread/QRunnable) for file scanning to avoid blocking the main UI thread.
- **File System Monitoring**: `watchdog` library to detect file creations, deletions, and modifications to keep the index synced in real-time.

## Database Schema (SQLite)
To support a workspace containing multiple directories or specific files, the schema must map one workspace to many paths:
1. `workspace`: id, name, created_at
2. `workspace_path`: id, workspace_id, root_path, type (folder/file)
3. `file_entry`: id, workspace_id, relative_path, absolute_path, file_type
4. `tags`: id, file_id, tag_name

## GUI Layout & Features
- **Left Area (Workspace List)**
  - List of loaded workspaces.
  - Can be rearranged (drag to scroll vertically).
  - Button/Action to "New Workspace" (opens dialog).
  - Workspace items have "Edit" and "Delete" actions.
  - **Workspace Dialog (New/Edit)**:
    - Input: Workspace Name (Text Field)
    - Input: A List/Table of paths belonging to this Workspace.
    - Action: "Add Folder" button (opens OS directory picker)
    - Action: "Add File" button (opens OS file picker)
    - Action: "Remove" button next to each added path in the list (button text should display fully without being cut off).
    - Action: Save / Cancel
- **Middle Separator**
  - `QSplitter` to allow resizing the left and right areas dynamically.
- **Right Area (Top)**
  - Search input box.
  - Clear button to reset search.
  - Search logic: case-insensitive, matches file path OR tag name (partial match: if tag name contains the keyword, it's a match), supports multiple keywords separated by `;` or `；`.
- **Right Area (Bottom)**
  - Implemented using `QTreeView` or `QTableView` with a `QAbstractTableModel` for lazy-loading/performance.
  - Displays: File Icon, Relative/Absolute Path, Tags.
  - The columns in the file list must be horizontally adjustable (resizable via dragging) by the user.
  - Checked boxes next to paths for batch operations.
  - **Tags UI**: Rendered as visually distinct pills/badges (colored background, rounded corners, padding) via custom PySide6 delegate.
- **Context Menu (Right Area)**
  - Assign/Edit Tag(s) (opens Dialog)
    - **Tag Dialog**:
      - Displays currently assigned tags as selectable/removable pills.
      - Input: Text field to type a new tag name. Pressing Enter or clicking "Add" adds it to the list.
      - Auto-completion/Suggestions: Shows a dropdown of existing tags used across the database as the user types.
      - Action: Apply / Cancel
  - Open File (Using system default application)
  - Reveal in Explorer/Finder
  - Open in Terminal (Opens the system terminal at the file's current path, supporting macOS and Windows)
  - Copy File Path
  - Delete File (Move to Recycle Bin via `send2trash` or similar)
  - Remove from Workspace (Removes index entry, does not delete actual file)

## UI / UX Aesthetics Requirements
Claude MUST implement the PySide6 UI with a modern, sleek aesthetic. Do not use default, native gray Windows 95 styling.
- **Theme**: A deep Dark Mode theme (similar to VSCode or Cursor or Linear). Backgrounds should be dark gray/blue, text should be off-white or light gray.
- **Layout Proportions**: The left sidebar should take up roughly 20-25% of the window width by default.
- **Tag Rendering**: Tags are the core feature. They must NEVER be rendered as plain text comma-separated strings.
  - They must be rendered as "Pills" or "Badges".
  - They must have a distinct background color (e.g., using a hash of the tag string to generate a pastel/vibrant color, or a set palette of colors).
  - They must have rounded corners (`border-radius`), horizontal and vertical padding, and appropriate contrasting text color.
- **Interactions**:
  - The active Workspace in the left list should have a distinct highlight background color (e.g., a modern accent blue) and rounded corners on the highlight box.
  - Hover effects: Rows in the file list and workspaces should subtly change background color on hover.
  - Clean borders: Avoid harsh deeply inset borders for widgets; use 1px solid subtle borders or rely on background color differences to separate areas (`QSplitter` handle should be thin and subtle).

## CLI Features (AI Agent Skill)
- Connects to the same SQLite database.
- Outputs JSON format for machine-readability.
- Commands (examples):
  - `search --tags "bug,urgent"`
  - `search --keyword "main"`
  - `list-files --workspace "MyProject"`
  - `get-tags --path "src/main.py"`
  - `add-tag --path "src/main.py" --tag "TODO"`

## Packaging and Distribution
- **Tool**: `PyInstaller` will be used to package the Python scripts, dependencies, and SQLite driver into standalone executables.
- **Windows**: Build script (`build_windows.bat` or `.ps1`) will generate a single `.exe` file.
- **macOS**: Build script (`build_mac.sh`) will generate a `.app` bundle / raw executable.
- Since CLI and GUI share the same core logic, consider generating two distinct entry points (one for GUI, one for CLI) or a single binary that switches to CLI mode when run with command-line arguments.
