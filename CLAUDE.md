# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A dual-interface (GUI + CLI) Python application for indexing, navigating, and tagging files across multiple named workspaces. The GUI uses PySide6 (Qt6), the CLI uses Click, and both share a common SQLite-backed core layer.

## Commands

### Run the application
```bash
python launch_gui.py          # Launch GUI
python cli/main.py --help     # CLI entry point
python cli/main.py list-files --workspace "MyWorkspace"
```

### Run tests
```bash
python -m pytest tests/ -v                                          # All tests
python -m pytest tests/test_scanner.py -v                          # Single file
python -m pytest tests/test_models_workspace.py::TestWorkspaceModel::test_create_workspace_success -v  # Single test
```

### Build standalone executables
```bash
python build.py               # Cross-platform (creates dist/)
.\build_windows.bat --clean   # Windows Batch Script
./build_mac.sh                # macOS
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Architecture

The application is split into three layers, all sharing the same SQLite database at `~/.workspace_indexer/workspace_indexer.db`:

```
core/    ← Single source of truth; GUI and CLI both import from here only
gui/     ← PySide6 interface; never accesses DB directly
cli/     ← Click-based interface; never accesses DB directly
tests/   ← pytest suite
specs/   ← Project specifications, feature requests, and bug trackers
```

### Core Layer (`core/`)
- **`db.py`**: Database init, `get_connection()` (enables foreign keys + row_factory), `initialize_database()`
- **`models.py`**: Four model classes (`Workspace`, `WorkspacePath`, `FileEntry`, `Tag`) — all CRUD lives here
- **`scanner.py`**: `FilesystemScanner` — recursively indexes workspace paths, skips hidden files (dot-prefix and Windows hidden attribute)
- **`watcher.py`**: `FilesystemWatcher` wraps watchdog.Observer for real-time index updates. Use `get_global_watcher()` for the singleton instance.

### GUI Layer (`gui/`)
- **`main_window.py`**: `MainWindow` (QMainWindow) with left workspace sidebar + right file table. `WorkspaceListWidget` emits signals (`workspace_selected`, `edit_requested`, `delete_requested`) consumed by `MainWindow`.
- **`dialogs.py`**: `WorkspaceDialog` (create/edit workspaces + path management), `TagDialog` (tag assignment with autocomplete pills)
- **`models.py`**: `FileTableModel` (QAbstractTableModel) — columns: Relative Path, File Type, Absolute Path, Tags
- **`delegates.py`**: `TagPillDelegate` (QStyledItemDelegate) — renders tags as colored rounded pills; color is deterministically derived from tag name hash

### CLI Layer (`cli/`)
- All commands output JSON for machine-readability
- Commands: `list-files`, `get-tags`, `add-tag`, `search` (keyword and/or tags), `--version`

## Key Patterns

- **No direct SQL outside `core/`**: All database access must go through the model classes in `core/models.py`.
- **Hidden file exclusion**: Both scanner and watcher exclude dot-prefixed names and Windows hidden-attribute files via `_is_hidden()`.
- **Threading**: File scanning runs in a QThread to avoid blocking the GUI; watchdog observer runs in its own thread.
- **Database schema**: Four tables — `workspace`, `workspace_path`, `file_entry`, `tags` — with CASCADE DELETE on workspace removal.

## Test Coverage

160 tests across 10 modules covering DB, models (workspace/path/tag), scanner, watcher, CLI, GUI models, delegates, and integration. One test is intentionally skipped (file rename detection on Windows).
