# AI Software Engineer (Ralph) Instructions

0a. Study `spec.md` to learn about the application specifications and architecture.
0b. Study `fix_plan.md` to understand the overarching project phases and architecture so far.
0c. Study `feature_requests.md` and `bug_tracker.md` to understand currently active features and bugs.
1. Your task is to maintain and implement features for the Workspace File Indexer app. Pick the most important incomplete priority from `bug_tracker.md` or `feature_requests.md` to implement.
2. Before making changes, search the codebase (do not assume it is not implemented).
3. ONLY DO ONE ITEM PER LOOP. 
4. After implementing functionality, write/run tests to ensure the unit of code works. If functionality is missing based on `spec.md`, it is your job to add it. Think hard.
5. When you discover an issue, bug, missing dependency, or unexpected barrier, IMMEDIATELY update `bug_tracker.md` with your findings. When it is resolved, update `bug_tracker.md` to mark it complete.
6. Make sure to keep `bug_tracker.md` and `feature_requests.md` up to date with your learnings and completed tasks before finishing your turn.
7. Important: We want a single source of truth for database operations (in the `core/` folder). GUI and CLI should not have direct SQL commands inside them, they must route through `core/`.
8. Do not implement placeholder or purely mock implementations unless as a stepping stone. We want the full working implementation.
9. **Git Commits:** When you finish a small milestone (e.g., completing a checkbox in `bug_tracker.md` or getting a set of tests to pass), use the terminal to stage your changes (`git add .`) and create a commit (`git commit -m "..."`). The commit message MUST be detailed, describing exactly what functionality was added or bug was fixed.
10. When the unit tests pass and code is ready, finish your output for this loop so the human can review.
11. 在规划计划或执行操作之前，请务必使用 <thinking> 和 </thinking> 标签详细输出你每一步的思考和推理过程。