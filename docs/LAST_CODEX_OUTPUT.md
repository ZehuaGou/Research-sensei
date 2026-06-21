# Last Codex Output

## 1. Commit

- commit hash (parent): `9f3173a`
- branch: main
- git status --short: see below

## 2. Task Summary

Cleanup session: removed stale legacy code and consolidated project status authority.

## 3. Fixes Applied

### P1: STATUS.md duplicate sections — FIXED
Removed outdated first copy of `## Largest Current Shortfalls`,
`## Next Priority Order`, and `## Weak-Model Handoff Guide`.
Each section now appears exactly once.

### P2: pytest-asyncio configuration — FIXED
Added `asyncio_default_fixture_loop_scope = "function"` to `pyproject.toml`.
Verified: `python -W error::DeprecationWarning -m pytest` passes cleanly.

### P3: .tmp_pytest* directories — NOT DELETED
Five `.tmp_pytest*` directories remain due to Windows permission corruption
(PermissionError [WinError 5]). `rmdir`, `takeown`, `icacls`,
`shutil.rmtree` all fail. They are covered by `.gitignore` and do not
affect tests or builds.

### P4: backend/ (dead code) — DELETED (26 files)
Zero imports of `backend.*` exist outside the deleted `legacy_tests/`.
All tests and scripts use `src/researchsensei/` (131 import sites).
`start.bat` (only external reference, pointed to `backend.web`) was also deleted.

### P5: legacy_tests/ and tests_e2e/ — DELETED
`legacy_tests/` (13 files) and `tests_e2e/` (2 files) removed. Both were
already `--ignore`d by pytest since 2026-06-03. Removed stale `--ignore`
flags from `pyproject.toml`. Removed `"legacy_tests"` from path exclusion
in `scripts/m1_target_mode_eval.py`.

### P6: RS设计文档权威冲突 — MOVED TO docs/archive/
`RS设计文档.md` moved to `docs/archive/` with header disclaimer
marking it as historical (non-authoritative) design reference.
Zero references existed in the codebase.

## 4. Test Results

| Suite | Result |
|---|---|
| Backend pytest | 565 passed, 15 skipped (0 failed) |
| Frontend vitest | 6 files, 42 passed |
| Frontend vite build | Built successfully |

## 5. Current Strict State

- No new features. No gates relaxed. M4 not started.
- Single authoritative status: `docs/STATUS.md`.
