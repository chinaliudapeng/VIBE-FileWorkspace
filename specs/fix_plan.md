# The Plan

## Phase 1: Project Setup and Infrastructure ✅ COMPLETED
- [x] Initialize Python environment, prepare `requirements.txt` with `pyside6`, `watchdog`, `send2trash`, `click`, etc.
- [x] Setup folder structure (`core/`, `gui/`, `cli/`, `tests/`).
- [x] Define the SQLite Database schema and create the initialization script (`core/db.py`).
- [x] Write unit tests to verify the database file is created and tables are exactly as defined in `spec.md`.
## Phase 2: Core Data Layer (CRUD) ✅ COMPLETED
- [x] Implement CRUD operations for Workspaces in `core/models.py` (Create Workspace, List Workspaces, Delete Workspace).
- [x] Write unit tests for Workspace CRUD operations.
- [x] Implement CRUD operations for Workspace Paths (Add Path to Workspace, Remove Path).
- [x] Write unit tests for Workspace Paths CRUD operations.
- [x] Implement CRUD operations for Tags (Add Tag to File, Remove Tag from File, Get all Tags for File, Get all unique Tags in DB).
- [x] Write unit tests for Tag CRUD operations.
## Phase 3: Core Scanner & Monitoring ✅ COMPLETED
- [x] Implement initial filesystem scanner (`core/scanner.py`) to populate the `file_entry` table for a given Workspace root path.
- [x] Write unit tests for the scanner using a temporary directory structure.
- [x] Implement `watchdog` integration (`core/watcher.py`) to detect file additions/deletions and update the database accordingly.
- [x] Write tests/mocks to verify `watchdog` correctly updates the `file_entry` table.
## Phase 4: CLI Implementation ✅ COMPLETED
- [x] Create basic CLI structure using `click` or `argparse` in `cli/main.py`.
- [x] Implement CLI command: `list-files --workspace <name>` and format output as JSON.
- [x] Implement CLI command: `get-tags --path <absolute_path>` and format output as JSON.
- [x] Implement CLI command: `add-tag --path <absolute_path> --tag <name>`.
- [x] Implement CLI command: `search --keyword` and `search --tags`, outputting JSON.
- [x] Write integration tests for the CLI to ensure it interacts correctly with the Core Data Layer.
- [x] Commit Git.
## Phase 5: GUI Foundation ✅ COMPLETED
- [x] Create the basic PySide6 `MainWindow` application shell (`gui/main_window.py`).
- [x] Implement the main layout with a horizontal `QSplitter` separating the left and right areas.
- [x] Implement the `WorkspaceListWidget` for the left area displaying workspaces from the database.
- [x] Commit Git.
## Phase 6: GUI Workspace Dialogs ✅ COMPLETED
- [x] Implement the "New/Edit Workspace" Dialog UI (`gui/dialogs.py`).
- [x] Implement functionality in the Workspace Dialog to add/remove folder and file paths.
- [x] Connect the Workspace Dialog to the database layer to save changes and refresh the `WorkspaceListWidget`.
- [x] Commit Git.
## Phase 7: GUI File View & Models
- [x] Implement `QAbstractTableModel` for the bottom right area to display `file_entry` data efficiently.
- [x] Implement the Table/Tree View in the bottom right area and connect it to the custom Model.
- [x] Implement the Top Right Area with a Search Input box and Clear button.
- [x] Connect the Search Input to the Model/Database to filter the displayed files dynamically.
- [x] Commit Git.
## Phase 7: ✅ COMPLETED
**Phase 7 is now fully completed with comprehensive file table view and dynamic search functionality.**

## Phase 8: GUI Tag Rendering & Interactions
- [x] Implement a custom PySide6 Delegate to render Tags as Pills/Badges within the Table/Tree View.
- [x] Implement right-click Context Menu for files (Open, Reveal, Copy Path, Delete, Remove from Workspace).
- [x] Implement the "Tag Dialog" UI to assign/edit/remove tags for selected files.
- [x] Connect the "Tag Dialog" to the database to persist tag changes and refresh the view.
- [x] Implement auto-completion in the Tag Dialog based on existing tags in the database.
- [x] Commit Git.
## Phase 8: ✅ COMPLETED
**Phase 8 is now fully completed with comprehensive tag rendering, context menu actions, and tag assignment dialog integration.**

## Phase 9: Packaging and Polish ✅ COMPLETED
- [x] Perform manual end-to-end testing of the GUI and CLI, ensuring no UI thread blocking during scanning.
- [x] Write the `build_windows.ps1` (or `.bat`) script using PyInstaller.
- [x] Write the `build_mac.sh` script using PyInstaller.
- [x] Verify the final packaged executables work on their respective operating systems.
- [x] Commit Git.
## Phase 9: ✅ COMPLETED
**Phase 9 is now fully completed with comprehensive packaging, testing, and cross-platform build script creation.**


## Note on Trackers
To keep this document lightweight, active tasks have been split into:
- **Features & Enhancements**: Please refer to eature_requests.md
- **Bugs & Issues**: Please refer to ug_tracker.md
- **Completed Tasks History**: Please refer to rchive_plan.md
