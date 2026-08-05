# Project Guidelines

## Code Style
- Keep edits minimal and scoped to the request; avoid broad refactors unless explicitly asked.
- Preserve existing module boundaries: app orchestration in `main.py`, engine logic in `core/`, UI widgets/dialogs in `ui/`.
- Prefer path helpers from `core/paths.py` for runtime file locations; do not hardcode install-specific paths.
- Keep Windows-first behavior intact (hotkeys, tray, packaging, installer flow).

## Architecture
- Entry point and lifecycle orchestration: `main.py` (`BabelGGApp` startup, tray/hotkeys, first-run checks, single-instance lock).
- Core services:
  - `core/flash.py`: translation/router and fallback logic.
  - `core/catch.py`: clipboard ingestion, filtering, and rate limiting.
  - `core/ocr.py`: OCR abstraction and backend handling.
  - `core/vault.py`: cache layer.
  - `core/license.py`, `core/telemetry.py`: licensing/telemetry concerns.
- UI surfaces live in `ui/` (`card.py`, `reply.py`, `settings.py`, `tray.py`, `downloader.py`, `ocr_overlay.py`).
- Packaging/runtime split matters: source mode vs frozen mode paths are handled by `core/paths.py`.

## Build and Test
- Install dependencies: `pip install -r requirements.txt`
- First-run model bootstrap (source/dev): `python download_models.py`
- Run app from source: `python main.py`
- Canonical tests: `python tests/run_all.py`
- Extended tests: `python tests/run_all.py --extended`
- Canonical release flow: `.\release.ps1` (supports `-SkipTests`, `-SkipExtendedTests`).
- In this workspace, prefer the VS Code task "Run BabelGG tests" for routine test runs.

## Conventions
- Use `tests/run_all.py` as the source of truth for test execution order and environment flags.
- Do not assume plain pytest discovery reflects CI/release behavior; release script drives quality gates.
- In frozen builds, writable app data/config/cache paths must remain under LOCALAPPDATA via `core/paths.py`.
- If changing translation routing (`core/flash.py`) or clipboard heuristics (`core/catch.py`), run relevant tests and avoid regressions in timeout/fallback behavior.

## Common Pitfalls
- Installer build requires Inno Setup (`ISCC.exe`) available; `release.ps1` fails early if missing.
- Global hotkeys can partially fail based on permissions or missing keyboard backend.
- App startup may depend on first-run model download; cancellation can exit startup.
- OCR behavior depends on backend/runtime availability (e.g., EasyOCR or Windows language packs).

## Project Docs
- Start here: `README.md`
- Architecture and router rationale: `build.md`
- Roadmap: `PLAN_2026-04-06.md`
- Current implementation progress and investigations: `PROGRESS_REPORT_2026-04-07.md`
- Release gates/checklist: `RELEASE_CHECKLIST_2026-04-06.md`
- Release audit/readiness notes: `RELEASE_AUDIT_2026-03-15.md`
- Installer smoke checklist: `installer/SMOKE_TEST_CHECKLIST.md`
