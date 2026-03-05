# Bug Tracker

This file tracks bugs and issues for the Workspace File Indexer.
When starting to fix a bug, pick the highest priority item from this list.
Update the status with [x] when completed.

## Bug 202603052033 - Analytics Test Mock Configuration Error (HIGH PRIORITY) ✅ COMPLETED
- [x] Fix test_analytics_with_real_data() in tests/test_analytics.py failing due to improperly configured mock ✅ COMPLETED
- [x] Issue: @patch('core.models.validate_workspace_path') mock is returning MagicMock object instead of string path ✅ COMPLETED
- [x] Error: sqlite3.ProgrammingError: Error binding parameter 2: type 'MagicMock' is not supported ✅ COMPLETED
- [x] Solution: Configure mock to return proper string value instead of MagicMock object ✅ COMPLETED
- [x] Fixed additional issue: WorkspacePath object used p.type instead of p.path_type in analytics.py (lines 113 and 360) ✅ COMPLETED
- [x] Fixed test isolation issues with unique file paths and adjusted assertions for integration tests ✅ COMPLETED
- [x] Verify all analytics tests pass after fix ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

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
- [x] Git commit and push ✅ COMPLETED

## Bug 202603031129 ✅ COMPLETED
- [x] Workspace编辑面板内remove按钮与忽略列表的文本看不全,需要调整按钮的大小与文本距离边缘的样式,避免文本看不到. ✅ COMPLETED
- [x] 自行测试 ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603031414 ✅ COMPLETED
- [x] Workspace编辑面板内路径忽略列表的文本看不全,需要调整背景大小与文本距离边缘的样式,避免文本看不到. ✅ COMPLETED
- [x] Workspace编辑面板内remove按钮超出行高了,需要你自行调整到适配行高的大小,但也要避免文本显示不全. ✅ COMPLETED
- [x] 自行测试 ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603031427 ✅ COMPLETED
- [x] 打开软件如果没有找到SQLite文件或者里面表不存在,那么初始化SQLite数据库,并建表. ✅ COMPLETED
- [x] Workspace编辑面板内remove按钮超出行高了,需要你自行调整到适配行高的大小,但也要避免文本显示不全. ✅ COMPLETED
- [x] 自行测试 ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603032030 - Security: Path Validation Vulnerability (CRITICAL PRIORITY) ✅ COMPLETED
- [x] Add path validation to WorkspacePath.add_path() to prevent path traversal and symlink escape attacks ✅ COMPLETED
- [x] Implement validation for: path traversal sequences (..), invalid characters, symlink resolution, path length limits ✅ COMPLETED
- [x] Replace TOCTOU (Time-of-Check-Time-of-Use) race conditions in core/scanner.py with try-except error handling ✅ COMPLETED
- [x] Add specific exception logging for Windows API calls in _is_hidden() functions ✅ COMPLETED
- [x] Write comprehensive security tests to verify path validation works correctly ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603031537 - Test Suite Failures Due to Strict Path Validation (CRITICAL PRIORITY) ✅ COMPLETED
- [x] Path validation from Bug 202603032030 is too strict for test cases using non-existent mock paths (e.g., `/test/bulk`, `/test/path`) ✅ COMPLETED
- [x] Multiple test failures in test_bulk_tag_loading.py, test_gui_delegates.py, test_gui_models.py due to `Directory does not exist` validation errors ✅ COMPLETED
- [x] Need to implement test-friendly path validation that allows mock paths during testing while maintaining security in production ✅ COMPLETED
- [x] Fix all affected test files to work with new validation approach ✅ COMPLETED
- [x] Run comprehensive test suite to ensure all tests pass for mentioned modules ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603051644 - Security Path Validation Test Failures (CRITICAL PRIORITY) ✅ COMPLETED
- [x] Fix error message mismatches in security validation tests causing 5 test failures ✅ COMPLETED
- [x] Issue 1: test_empty_path_validation expects "Path cannot be empty" but gets "root_path cannot be empty" ✅ COMPLETED
- [x] Issue 2: test_invalid_characters_windows expects "invalid characters" but gets specific character error messages ✅ COMPLETED
- [x] Issue 3: test_trailing_dots_spaces_windows has regex mismatch issues ✅ COMPLETED
- [x] Issue 4: test_race_condition_mitigation has implementation/test expectation mismatch ✅ COMPLETED
- [x] Issue 5: test_error_messages_safe expects "Invalid path format" or "Cannot access path" but gets "File does not exist" ✅ COMPLETED
- [x] Align error messages between validation implementation and test expectations ✅ COMPLETED
- [x] Run security validation tests to ensure all pass ✅ COMPLETED
- [x] Fix final edge case in test_add_path_whitespace_trimming that conflicted with Windows path component validation ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

**Final Summary**: Successfully resolved all test failures related to security path validation. All 238 tests now pass (235 passed, 3 skipped, 0 failed). Fixed the edge case where whitespace trimming test was creating path components with trailing spaces, which correctly triggered Windows security validation. Adjusted test to validate leading whitespace trimming without violating security rules.

## Bug 202603052000 - 检查一下workspace编辑面板,已添加路径列列中remove_btn超出所在行的单元格大小,hiding_rules列中的元素的大小过小以至于文本显示不出来,解决这两个问题 ✅ COMPLETED
- [x] 解决界面上的显示问题 ✅ COMPLETED
  - Fixed remove button sizing to fit within 40px row height (reduced from 24px to 20px height, adjusted margins from 5px to 2-3px)
  - Improved hiding rules pill display with increased height (30px to 32px), better padding (10,4,6,4 to 12,6,8,6), larger font (12px to 13px)
  - Made Edit button consistent with Remove button sizing (both now 48px width, 20px height)
- [x] Run security validation tests to ensure all pass ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603051943 - workspace编辑面板加宽50像素,将remove_btn所在的列的宽度加宽50像素 ✅ COMPLETED
- [x] 解决界面上的显示问题 ✅ COMPLETED
  - Widened workspace editing panel by 50 pixels (minimum size: 600→650px, default size: 700→750px)
  - Widened remove button column by 50 pixels (from 70px to 120px width)
- [x] 自行测试 ✅ COMPLETED
- [x] Git commit and push ✅ COMPLETED

## Bug 202603052007 - workspace编辑面板移除remove_btn所在的容器背景颜色 ✅ COMPLETED
- [x] 解决界面上的显示问题 ✅ COMPLETED
  - Fixed by adding `container.setStyleSheet("background-color: transparent;")` to remove button container in WorkspaceDialog
  - Container widget now has transparent background, removing unwanted background color
- [x] 自行测试 ✅ COMPLETED
  - GUI integration tests pass (15/15 tests)
  - GUI workflow tests pass (1/1 test)
- [x] Git commit and push ✅ COMPLETED