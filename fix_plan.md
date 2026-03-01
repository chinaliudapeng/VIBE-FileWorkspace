# The Plan

## Phase 1: Project Setup and Infrastructure ✅ COMPLETED
- [x] Initialize Python environment, prepare `requirements.txt` with `pyside6`, `watchdog`, `send2trash`, `click`, etc.
- [x] Setup folder structure (`core/`, `gui/`, `cli/`, `tests/`).
- [x] Define the SQLite Database schema and create the initialization script (`core/db.py`).
- [x] Write unit tests to verify the database file is created and tables are exactly as defined in `spec.md`.

### Phase 1 Learnings:
- Database uses `~/.workspace_indexer/workspace_indexer.db` as the default location
- SQLite PRIMARY KEY columns don't show NOT NULL explicitly in schema inspection (handled in tests)
- All foreign key constraints properly set up with CASCADE DELETE for data integrity
- Added performance indexes on commonly queried columns
- 9/9 unit tests passing, schema matches specification exactly

## Phase 2: Core Data Layer (CRUD)
- [x] Implement CRUD operations for Workspaces in `core/models.py` (Create Workspace, List Workspaces, Delete Workspace).
- [x] Write unit tests for Workspace CRUD operations.
- [ ] Implement CRUD operations for Workspace Paths (Add Path to Workspace, Remove Path).
- [ ] Write unit tests for Workspace Paths CRUD operations.
- [ ] Implement CRUD operations for Tags (Add Tag to File, Remove Tag from File, Get all Tags for File, Get all unique Tags in DB).
- [ ] Write unit tests for Tag CRUD operations.

### Phase 2 Learnings:
- Workspace model implemented with comprehensive CRUD operations
- Added business logic validation: workspace names cannot be empty or whitespace-only
- All foreign key CASCADE DELETE constraints work properly for workspace deletion
- Created 18 unit tests covering all workspace operations, edge cases, and error conditions
- Total test count: 27 tests (9 database + 18 workspace) - all passing

## Phase 3: Core Scanner & Monitoring
- [ ] Implement initial filesystem scanner (`core/scanner.py`) to populate the `file_entry` table for a given Workspace root path.
- [ ] Write unit tests for the scanner using a temporary directory structure.
- [ ] Implement `watchdog` integration (`core/watcher.py`) to detect file additions/deletions and update the database accordingly.
- [ ] Write tests/mocks to verify `watchdog` correctly updates the `file_entry` table.

## Phase 4: CLI Implementation
- [ ] Create basic CLI structure using `click` or `argparse` in `cli/main.py`.
- [ ] Implement CLI command: `list-files --workspace <name>` and format output as JSON.
- [ ] Implement CLI command: `get-tags --path <absolute_path>` and format output as JSON.
- [ ] Implement CLI command: `add-tag --path <absolute_path> --tag <name>`.
- [ ] Implement CLI command: `search --keyword` and `search --tags`, outputting JSON.
- [ ] Write integration tests for the CLI to ensure it interacts correctly with the Core Data Layer.

## Phase 5: GUI Foundation
- [ ] Create the basic PySide6 `MainWindow` application shell (`gui/main_window.py`).
- [ ] Implement the main layout with a horizontal `QSplitter` separating the left and right areas.
- [ ] Implement the `WorkspaceListWidget` for the left area displaying workspaces from the database.

## Phase 6: GUI Workspace Dialogs
- [ ] Implement the "New/Edit Workspace" Dialog UI (`gui/dialogs.py`).
- [ ] Implement functionality in the Workspace Dialog to add/remove folder and file paths.
- [ ] Connect the Workspace Dialog to the database layer to save changes and refresh the `WorkspaceListWidget`.

## Phase 7: GUI File View & Models
- [ ] Implement `QAbstractTableModel` for the bottom right area to display `file_entry` data efficiently.
- [ ] Implement the Table/Tree View in the bottom right area and connect it to the custom Model.
- [ ] Implement the Top Right Area with a Search Input box and Clear button.
- [ ] Connect the Search Input to the Model/Database to filter the displayed files dynamically.

## Phase 8: GUI Tag Rendering & Interactions
- [ ] Implement a custom PySide6 Delegate to render Tags as Pills/Badges within the Table/Tree View.
- [ ] Implement right-click Context Menu for files (Open, Reveal, Copy Path, Delete, Remove from Workspace).
- [ ] Implement the "Tag Dialog" UI to assign/edit/remove tags for selected files.
- [ ] Connect the "Tag Dialog" to the database to persist tag changes and refresh the view.
- [ ] Implement auto-completion in the Tag Dialog based on existing tags in the database.

## Phase 9: Packaging and Polish
- [ ] Perform manual end-to-end testing of the GUI and CLI, ensuring no UI thread blocking during scanning.
- [ ] Write the `build_windows.ps1` (or `.bat`) script using PyInstaller.
- [ ] Write the `build_mac.sh` script using PyInstaller.
- [ ] Verify the final packaged executables work on their respective operating systems.
