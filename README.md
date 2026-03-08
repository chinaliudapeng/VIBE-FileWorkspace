# Workspace File Indexer

A dual-interface (GUI + CLI) Python application for indexing, navigating, and tagging files across multiple named workspaces. The GUI is built with PySide6 (Qt6), the CLI uses Click, and both share a common SQLite-backed core layer.

---

## Features

- **Multiple Workspaces** — organize files into named workspaces, each with one or more root paths
- **Auto Indexing** — recursively scans workspace paths and indexes all non-hidden files into SQLite
- **Real-time Watching** — file system watcher keeps the index up to date as files change on disk
- **Tag System** — assign arbitrary tags to files; rendered as colored pills in the GUI
- **Search** — find files by keyword, tags, or both, optionally scoped to a workspace
- **Analytics** — built-in statistics: file type distributions, tag coverage, database metrics
- **AI-agent Ready CLI** — all CLI commands output JSON, designed for machine consumption
- **Hidden File Exclusion** — automatically skips dot-prefixed names and Windows hidden-attribute files
- **Standalone Executables** — PyInstaller build scripts for Windows and macOS

---

## Screenshots

> GUI application with workspace sidebar and file table (tags displayed as colored pills)

---

## Architecture

All layers share a single SQLite database at `~/.workspace_indexer/workspace_indexer.db`.

```
core/    ← Single source of truth; GUI and CLI both import from here only
gui/     ← PySide6 Qt6 interface; never accesses DB directly
cli/     ← Click-based interface; never accesses DB directly
tests/   ← pytest suite (253+ tests)
specs/   ← Project specifications, feature requests, and bug trackers
```

### Core Layer (`core/`)

| File | Description |
|---|---|
| `db.py` | Database init, `get_connection()` (enables foreign keys + row_factory), `initialize_database()` |
| `models.py` | Four model classes (`Workspace`, `WorkspacePath`, `FileEntry`, `Tag`) — all CRUD lives here |
| `scanner.py` | `FilesystemScanner` — recursively indexes workspace paths, skips hidden files |
| `watcher.py` | `FilesystemWatcher` wraps watchdog.Observer for real-time index updates |
| `analytics.py` | `WorkspaceAnalytics` — statistics for workspaces, files, tags, and database |
| `logging_config.py` | Centralized logging configuration used throughout core modules |

### GUI Layer (`gui/`)

| File | Description |
|---|---|
| `main_window.py` | `MainWindow` (QMainWindow) with left workspace sidebar + right file table |
| `dialogs.py` | `WorkspaceDialog` (create/edit), `TagDialog` (tag assignment with autocomplete pills) |
| `models.py` | `FileTableModel` (QAbstractTableModel) — columns: Relative Path, File Type, Absolute Path, Tags |
| `delegates.py` | `TagPillDelegate` — renders tags as colored rounded pills (color derived from tag name hash) |

### CLI Layer (`cli/`)

All commands output JSON. Commands:

| Command | Description |
|---|---|
| `list-workspaces` | List all workspaces |
| `list-files -w <name>` | List all files in a workspace |
| `search -k <keyword>` | Search files by keyword |
| `search -t <tag1,tag2>` | Search files by tags |
| `get-tags -p <path>` | Get all tags on a file |
| `add-tag -p <path> -t <tag>` | Add a tag to a file |
| `remove-tag -p <path> -t <tag>` | Remove a tag from a file |
| `list-tags` | List all unique tags |
| `stats` | Get comprehensive analytics |

### Database Schema

Four tables with CASCADE DELETE on workspace removal:

```
workspace        → id, name, created_at
workspace_path   → id, workspace_id, root_path, path_type, hiding_rules
file_entry       → id, workspace_id, relative_path, absolute_path, file_type
tags             → id, file_id, tag_name
```

---

## Requirements

- Python 3.10+
- PySide6 >= 6.6.0
- watchdog >= 3.0.0
- click >= 8.1.0
- send2trash >= 1.8.2
- pytest >= 7.4.0 (for tests)
- pyinstaller >= 6.0.0 (for builds)

---

## Installation

```bash
git clone <repository-url>
cd VIBE-FileWorkspace
pip install -r requirements.txt
```

---

## Usage

### Launch GUI

```bash
python launch_gui.py
```

### CLI

```bash
# Show help
python cli/main.py --help

# List all workspaces
python cli/main.py list-workspaces

# List files in a workspace
python cli/main.py list-files --workspace "MyWorkspace"

# Search by keyword
python cli/main.py search --keyword "report"

# Search by tags
python cli/main.py search --tags "important,review"

# Search by keyword + tags, scoped to workspace
python cli/main.py search --keyword "invoice" --tags "finance" --workspace "Work"

# Get tags on a file
python cli/main.py get-tags --path "/absolute/path/to/file.txt"

# Add a tag
python cli/main.py add-tag --path "/absolute/path/to/file.txt" --tag "important"

# Remove a tag
python cli/main.py remove-tag --path "/absolute/path/to/file.txt" --tag "important"

# List all tags
python cli/main.py list-tags

# Get comprehensive analytics
python cli/main.py stats

# Get stats for a specific workspace
python cli/main.py stats --workspace "MyWorkspace"

# Get specific stats type (comprehensive | database | workspaces | files | tags)
python cli/main.py stats --type tags
```

All CLI commands return JSON with the structure:

```json
{ "success": true, "data": { ... } }
{ "success": false, "error": "..." }
```

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Single module
python -m pytest tests/test_scanner.py -v

# Single test
python -m pytest tests/test_models_workspace.py::TestWorkspaceModel::test_create_workspace_success -v
```

253+ tests across 11 modules covering: DB, models (workspace/path/tag), scanner, watcher, CLI, GUI models, delegates, analytics, and integration. One test is intentionally skipped (file rename detection on Windows).

---

## Build Standalone Executables

```bash
# Cross-platform
python build.py

# Windows
.\build_windows.bat --clean

# macOS
./build_mac.sh
```

Output is placed in `dist/`.

---

## Key Design Patterns

- **No direct SQL outside `core/`** — all database access goes through model classes in `core/models.py`
- **Hidden file exclusion** — both scanner and watcher skip dot-prefixed names and Windows hidden-attribute files via `_is_hidden()`
- **Non-blocking GUI** — file scanning runs in a QThread; watchdog observer runs in its own thread
- **JSON CLI output** — all commands output structured JSON for easy integration with scripts and AI agents
- **Structured logging** — centralized in `core/logging_config.py` with timestamps and performance tracking

---

## Project Structure

```
VIBE-FileWorkspace/
├── launch_gui.py          # GUI entry point
├── requirements.txt
├── build.py               # Cross-platform build script
├── build_windows.bat
├── build_mac.sh
├── core/
│   ├── db.py
│   ├── models.py
│   ├── scanner.py
│   ├── watcher.py
│   ├── analytics.py
│   └── logging_config.py
├── gui/
│   ├── main_window.py
│   ├── dialogs.py
│   ├── models.py
│   └── delegates.py
├── cli/
│   └── main.py
├── tests/
│   ├── test_db.py
│   ├── test_scanner.py
│   ├── test_watcher.py
│   ├── test_models_workspace.py
│   ├── test_models_path.py
│   ├── test_models_tag.py
│   ├── test_cli.py
│   ├── test_gui_models.py
│   ├── test_delegates.py
│   ├── test_analytics.py
│   └── test_integration.py
└── specs/
    ├── spec.md
    ├── feature_requests.md
    └── bug_tracker.md
```

---

## License

This project is for private use. No license is currently specified.
