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

## Phase 2: Core Data Layer (CRUD) ✅ COMPLETED
- [x] Implement CRUD operations for Workspaces in `core/models.py` (Create Workspace, List Workspaces, Delete Workspace).
- [x] Write unit tests for Workspace CRUD operations.
- [x] Implement CRUD operations for Workspace Paths (Add Path to Workspace, Remove Path).
- [x] Write unit tests for Workspace Paths CRUD operations.
- [x] Implement CRUD operations for Tags (Add Tag to File, Remove Tag from File, Get all Tags for File, Get all unique Tags in DB).
- [x] Write unit tests for Tag CRUD operations.

### Phase 2 Learnings:
- Workspace model implemented with comprehensive CRUD operations
- Added business logic validation: workspace names cannot be empty or whitespace-only
- WorkspacePath model implemented with full CRUD operations supporting both files and folders
- Fixed critical issue: SQLite foreign key constraints were not enabled by default - added `PRAGMA foreign_keys = ON` to enable CASCADE DELETE functionality
- All foreign key CASCADE DELETE constraints work properly for workspace deletion (automatically removes workspace paths, file entries, and tags)
- WorkspacePath operations include validation for path types, workspace existence, and duplicate prevention
- Tag model implemented with comprehensive CRUD operations following established patterns
- Tag operations include validation for empty tag names, file existence, and duplicate prevention
- Tag foreign key constraints to file_entry work properly with CASCADE DELETE (tags auto-deleted when files are deleted)
- Unique constraint on (file_id, tag_name) prevents duplicate tags on same file
- Tag operations properly handle whitespace trimming and input validation
- Created 18 unit tests for workspace operations, 24 unit tests for workspace path operations, and 22 unit tests for tag operations
- Total test count: 73 tests (9 database + 18 workspace + 24 workspace path + 22 tag) - all passing

## Phase 3: Core Scanner & Monitoring ✅ COMPLETED
- [x] Implement initial filesystem scanner (`core/scanner.py`) to populate the `file_entry` table for a given Workspace root path.
- [x] Write unit tests for the scanner using a temporary directory structure.
- [x] Implement `watchdog` integration (`core/watcher.py`) to detect file additions/deletions and update the database accordingly.
- [x] Write tests/mocks to verify `watchdog` correctly updates the `file_entry` table.

### Phase 3 Learnings:
- Implemented comprehensive FileEntry model with full CRUD operations for managing file entries in database
- Created FilesystemScanner class that handles both individual files and recursive directory scanning
- File type detection based on extensions with proper fallback handling
- Scanner integrates seamlessly with existing Workspace and WorkspacePath models using foreign key relationships
- Added rescan functionality to detect filesystem changes (additions/deletions) and sync with database
- Implemented convenience functions scan_workspace() and rescan_workspace() for easy API usage
- **Implemented real-time filesystem monitoring using watchdog library (`core/watcher.py`)**:
  - Created WorkspaceFileHandler for handling filesystem events (create, delete, move/rename)
  - Implemented FilesystemWatcher class with thread-safe operations and proper observer lifecycle management
  - Supports watching multiple workspaces simultaneously with independent event handling
  - Handles file creation, deletion, and move/rename events with automatic database synchronization
  - Properly calculates relative paths for files within workspace boundaries
  - Ignores directory events (only tracks files as per specification)
  - Includes global watcher instance and convenience functions for easy integration
  - Context manager support for automatic cleanup
  - Fixed observer thread reuse issue by creating new Observer instances after shutdown
- Created comprehensive test suite covering both scanner (18 tests) and watcher (22 tests) functionality
- Tests use temporary database files to avoid interference, ensuring isolated and reliable testing
- Scanner and watcher properly handle missing paths, permission errors, and duplicate files gracefully
- Database foreign key CASCADE DELETE ensures file entries are automatically cleaned up when workspaces are deleted
- File entries include relative_path (from workspace root), absolute_path (unique), and detected file_type
- Total test count: 113 tests (9 database + 18 workspace + 24 workspace path + 22 tag + 18 scanner + 22 watcher) - all passing

## Phase 4: CLI Implementation ✅ COMPLETED
- [x] Create basic CLI structure using `click` or `argparse` in `cli/main.py`.
- [x] Implement CLI command: `list-files --workspace <name>` and format output as JSON.
- [x] Implement CLI command: `get-tags --path <absolute_path>` and format output as JSON.
- [x] Implement CLI command: `add-tag --path <absolute_path> --tag <name>`.
- [x] Implement CLI command: `search --keyword` and `search --tags`, outputting JSON.
- [x] Write integration tests for the CLI to ensure it interacts correctly with the Core Data Layer.
- [x] Commit Git.

### Phase 4 Learnings:
- **Implemented complete CLI interface using Click framework (`cli/main.py`)**:
  - Created professional command-line interface with help documentation and version info
  - All commands output machine-readable JSON format as required for AI agent integration
  - Consistent error handling with JSON error responses and appropriate exit codes
  - Added proper imports and path management to access core modules
- **All required CLI commands fully implemented**:
  - `list-files --workspace <name>`: Lists files in a workspace with metadata (relative path, absolute path, file type)
  - `get-tags --path <absolute_path>`: Returns all tags for a specific file
  - `add-tag --path <absolute_path> --tag <name>`: Adds tags to files with validation
  - `search --keyword <keyword>`: Searches file paths by keyword
  - `search --tags <tag1,tag2>`: Searches files by tag names (comma-separated)
  - `search --keyword <keyword> --tags <tags>`: Combined keyword and tag search
  - `search --workspace <name>`: Limits searches to specific workspace
- **Enhanced FileEntry model with comprehensive search functionality (`core/scanner.py`)**:
  - Added `search_by_keyword()` method for file path searches with optional workspace filtering
  - Added `search_by_tags()` method for tag-based searches with SQL JOIN operations
  - Added `search_by_keyword_and_tags()` method for combined searches
  - All search methods use efficient SQL queries with proper indexing and parameterization
- **Created comprehensive CLI test suite (`tests/test_cli.py`)**:
  - 8 integration tests covering all CLI commands and error scenarios
  - Tests use temporary database files for isolation and reliability
  - Tests verify JSON output format, error handling, and data integrity
  - Includes positive and negative test cases for robust validation
- **CLI properly integrates with existing core data layer**:
  - Uses same SQLite database as GUI application (single source of truth)
  - Leverages existing Workspace, WorkspacePath, FileEntry, and Tag models
  - Maintains data consistency and foreign key relationships
  - No direct SQL in CLI - all operations go through core models as required
- **Total test count: 121 tests (113 existing + 8 CLI) - all passing**
- **CLI ready for AI agent integration and packaging phase**

## Phase 5: GUI Foundation ✅ COMPLETED
- [x] Create the basic PySide6 `MainWindow` application shell (`gui/main_window.py`).
- [x] Implement the main layout with a horizontal `QSplitter` separating the left and right areas.
- [x] Implement the `WorkspaceListWidget` for the left area displaying workspaces from the database.
- [x] Commit Git.

### Phase 5 Learnings:
- **Implemented basic PySide6 MainWindow application shell (`gui/main_window.py`)**:
  - Created modern dark theme UI similar to VSCode/Cursor with proper color palette
  - Dark gray/blue backgrounds with off-white/light gray text for optimal readability
  - Modern aesthetics: rounded corners, subtle borders, hover effects, accent colors
  - Responsive layout with proper spacing and margins
- **Implemented horizontal QSplitter layout**:
  - Left sidebar takes 20-25% width by default (300px out of 1200px window)
  - Right area takes remaining 75% for search and file display
  - Splitter handle with hover effects and smooth resize capability
  - Proper responsive design maintaining proportions
- **Enhanced WorkspaceListWidget with database integration**:
  - Custom WorkspaceListWidget class extending QListWidget with database connectivity
  - Direct integration with core.models.Workspace using Workspace.list_all() method
  - Real-time workspace selection with signal/slot communication
  - Proper error handling for database connection issues
  - Auto-selection of first workspace when available
  - Refresh capability to reload workspaces from database
  - Workspace objects stored as QListWidgetItem user data for efficient access
- **GUI properly integrates with existing core data layer**:
  - Uses same SQLite database as CLI application (single source of truth)
  - No direct SQL in GUI - all operations route through core/ models as required
  - Maintains data consistency and foreign key relationships
  - Follows established patterns from CLI implementation
- **All 121 unit tests continue to pass** - no regressions introduced
- **GUI foundation ready for Phase 6 (Workspace Dialogs) implementation**

## Phase 6: GUI Workspace Dialogs
- [x] Implement the "New/Edit Workspace" Dialog UI (`gui/dialogs.py`).
- [x] Implement functionality in the Workspace Dialog to add/remove folder and file paths.
- [ ] Connect the Workspace Dialog to the database layer to save changes and refresh the `WorkspaceListWidget`.
- [ ] Commit Git.

### Phase 6 Learnings (In Progress):
- **Implemented comprehensive WorkspaceDialog class (`gui/dialogs.py`)**:
  - Single dialog handles both new workspace creation and editing existing workspaces
  - Modern dark theme UI consistent with main window styling
  - Workspace name input field with validation
  - Dynamic paths table showing folder/file paths with type indicators
  - Add Folder/Add File buttons using OS file/directory pickers
  - Remove button for each path with confirmation dialog
  - Proper error handling and user feedback via message boxes
  - Integrates with core.models (Workspace, WorkspacePath) for database operations
  - Save/Cancel buttons with form validation
  - Duplicate path detection and prevention
  - Tooltips showing full paths for long file names
- **Dialog features implemented**:
  - Alternating row colors in paths table for better readability
  - Resizable columns with appropriate sizing policies
  - Modal dialog prevents interaction with main window during editing
  - Proper form layout with consistent spacing and margins
  - Confirmation dialogs for destructive actions (removing paths)
  - Warning when creating workspace with no paths
- **Database integration**:
  - Uses existing Workspace.create() and WorkspacePath CRUD operations
  - Maintains single source of truth principle (no direct SQL in GUI)
  - Proper foreign key relationship handling
  - Transaction safety with error rollback
- **Still needed**: Connect dialog to main window's "New Workspace" button and implement workspace refresh after changes

## Phase 7: GUI File View & Models
- [ ] Implement `QAbstractTableModel` for the bottom right area to display `file_entry` data efficiently.
- [ ] Implement the Table/Tree View in the bottom right area and connect it to the custom Model.
- [ ] Implement the Top Right Area with a Search Input box and Clear button.
- [ ] Connect the Search Input to the Model/Database to filter the displayed files dynamically.
- [ ] Commit Git.

## Phase 8: GUI Tag Rendering & Interactions
- [ ] Implement a custom PySide6 Delegate to render Tags as Pills/Badges within the Table/Tree View.
- [ ] Implement right-click Context Menu for files (Open, Reveal, Copy Path, Delete, Remove from Workspace).
- [ ] Implement the "Tag Dialog" UI to assign/edit/remove tags for selected files.
- [ ] Connect the "Tag Dialog" to the database to persist tag changes and refresh the view.
- [ ] Implement auto-completion in the Tag Dialog based on existing tags in the database.
- [ ] Commit Git.

## Phase 9: Packaging and Polish
- [ ] Perform manual end-to-end testing of the GUI and CLI, ensuring no UI thread blocking during scanning.
- [ ] Write the `build_windows.ps1` (or `.bat`) script using PyInstaller.
- [ ] Write the `build_mac.sh` script using PyInstaller.
- [ ] Verify the final packaged executables work on their respective operating systems.
- [ ] Commit Git.
