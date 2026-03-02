# Bug Tracker

This file tracks bugs and issues for the Workspace File Indexer.
When starting to fix a bug, pick the highest priority item from this list.
Update the status with [x] when completed.

## Bug 202603022352 ✅ COMPLETED
- [x] Workspace编辑面板删除路径的按钮内文本看不全，需要调整按钮的样式. ✅ COMPLETED
- [x] 自行测试. ✅ COMPLETED
- [x] Git Commit and Push. ✅ COMPLETED

## Bug 202603030001 - Critical Code Quality Issues (HIGH PRIORITY) ✅ COMPLETED
- [x] Replace print statements with proper logger calls throughout codebase (affects production reliability) ✅ COMPLETED
- [x] Fix N+1 query problem in TagPillDelegate.paint() causing performance issues ✅ COMPLETED
- [x] Implement missing Workspace.update() method for renaming workspaces ✅ COMPLETED
- [x] Add validation for hiding rules regex patterns to prevent silent failures ✅ COMPLETED
- [x] Fix thread safety issues in FilesystemWatcher ✅ COMPLETED
- [x] Run comprehensive tests after fixes ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED
- [x] Wait human stop agent ✅ COMPLETED

## Bug 202603030002 - Test Failures (HIGH PRIORITY) ✅ COMPLETED
- [x] Fix TagPillDelegate paint method error: 'Mock' object is not iterable (gui/delegates.py:104) ✅ COMPLETED
- [x] Fix WorkspaceDialog.accept() not properly creating/updating workspaces ✅ COMPLETED
- [x] Investigate workspace rename functionality failure ✅ COMPLETED
- [x] Run comprehensive tests after fixes ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603030003 - Search Functionality Missing Spec Requirements (HIGH PRIORITY) ✅ COMPLETED
- [x] Fix case-insensitive search - currently using case-sensitive LIKE operator in SQLite queries (spec.md line 40 requirement) ✅ COMPLETED
- [x] Fix multiple keywords search - currently only uses first keyword despite parsing all keywords correctly ✅ COMPLETED
- [x] Update search methods in core/scanner.py to use LOWER() function for case-insensitive matching ✅ COMPLETED
- [x] Update GUI search handler in gui/main_window.py to process all parsed keywords, not just the first one ✅ COMPLETED
- [x] Run comprehensive tests after fixes to ensure case-insensitive search works correctly ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603030004 - Inconsistent Logging Standards (HIGH PRIORITY) ✅ COMPLETED
- [x] Fix remaining print() statement in gui/dialogs.py:573 that violates logging consistency established in Bug 202603030001 ✅ COMPLETED
- [x] Review and ensure all error messages use appropriate logger levels instead of print() statements ✅ COMPLETED
- [x] Run comprehensive tests to ensure logging changes don't break functionality ✅ COMPLETED
- [ ] Git commit and push
