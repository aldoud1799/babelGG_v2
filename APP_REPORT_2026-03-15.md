# BabelGG v2 Comprehensive Application Report

Date: 2026-03-15
Project Root: `BabelGG_v2`

## 1. Executive Summary

BabelGG v2 is a Windows-focused, real-time game translation application built with Python and PyQt6. It monitors copied text, detects language, translates with NLLB-200 (via CTranslate2), and presents results in a floating in-game card UI.

The codebase is modular and pragmatic, with clear separation between translation core, clipboard orchestration, cache, UI, and packaging/release assets. The project is release-capable with automated test execution and scripted installer generation.

## 2. Product Purpose and User Flow

Primary use case:
1. User copies foreign-language text (`Ctrl+C`) while gaming.
2. Clipboard monitor detects new content.
3. Text is normalized (emoji + slang handling), translated, and cached.
4. A floating card appears near cursor with translated text.
5. User can pin, dismiss, or open reply flow for reverse translation.

First-run behavior:
- If model assets are missing, a downloader flow launches to fetch/prepare models.

## 3. Repository and Structure Overview

Top-level role summary:
- `main.py`: startup, app orchestration, signal wiring, tray/hotkey lifecycle.
- `core/`: engine and business logic.
- `ui/`: PyQt6 presentation layer (card, settings, tray, reply, downloader, OCR overlay).
- `tests/`: unit/integration-style checks for core behaviors.
- `installer/`: Inno Setup script and installer artifacts.
- `BabelGG.spec` (+ variant specs): PyInstaller packaging definitions.
- `release.ps1`: canonical one-command release build flow.

Notable data/config assets:
- `config.json`: user/app runtime configuration.
- `version.json`: app/model version metadata.
- `data/vault.json`: translation cache persistence.
- `data/telemetry.json`: local telemetry/event records.

## 4. Architecture and Runtime Flow

Startup chain (high level):
1. Resolve runtime paths (source vs frozen executable).
2. Initialize logging and config.
3. Initialize tray/UI shell.
4. Initialize translation engine.
5. Load vault/cache.
6. Start clipboard monitor thread/process.
7. Register hotkeys and update checks.

Translation path:
1. Clipboard text arrives and is validated.
2. Cache lookup (exact, optional fuzzy).
3. Slang/emoji normalization.
4. Language detection + target routing.
5. CTranslate2/NLLB inference.
6. Post-processing and emit to UI card.
7. Telemetry log + cache store.

## 5. Core Modules and Responsibilities

- `core/flash.py`: translation engine, model/device setup, language routing.
- `core/catch.py`: clipboard polling and event trigger logic.
- `core/vault.py`: SHA/fuzzy cache strategy, persistence, LRU behavior.
- `core/slang.py`: gaming-term normalization map.
- `core/emoji_cleaner.py`: emoji cleanup helpers.
- `core/hardware.py`: CPU/GPU capability probing and runtime selection.
- `core/ocr.py`: OCR backend wiring and extraction utilities.
- `core/license.py`: feature gating/license state checks.
- `core/telemetry.py`: local event logging and metrics.
- `core/updater.py`: remote version polling and update signal path.

## 6. UI Layer Techniques

The UI is implemented with PyQt6 and organized by responsibility:
- `ui/card.py`: floating translation card interaction model.
- `ui/reply.py`: reverse-translation/reply composition.
- `ui/settings.py`: settings state editing and persistence hooks.
- `ui/tray.py`: tray icon/menu and app-level controls.
- `ui/downloader.py`: model download and first-run readiness UX.
- `ui/ocr_overlay.py`: visual OCR region selection support.

Design characteristics:
- Event-driven signal/slot communication.
- Defensive handling around model availability and first-run state.
- Runtime behavior tuned for near-real-time responsiveness.

## 7. Techniques and Technology Stack

- Language/runtime: Python 3.x
- UI: PyQt6
- Translation inference: CTranslate2 + NLLB model assets
- Language detection and text normalization: mixed heuristic + library-driven steps
- OCR: optional OCR path with backend abstraction
- Persistence: JSON files (config/cache/telemetry)
- Packaging: PyInstaller (onefile and variant specs)
- Installer: Inno Setup (ISCC)
- Testing: Python test suite (`tests/run_all.py`)

## 8. Build, Packaging, and Release Readiness

Current release pipeline:
1. Run tests.
2. Build EXE with PyInstaller.
3. Compile installer with Inno Setup.
4. Validate outputs.

Canonical command:
- `./release.ps1` (PowerShell)

Expected outputs:
- `dist/BabelGG.exe`
- `installer/BabelGG_Setup.exe`

Installer script:
- `installer/BabelGG.iss` defines application metadata, files, shortcuts, and launch behavior.

## 9. Test Strategy and Coverage Signals

The `tests/` suite focuses on core reliability:
- hardware detection
- translation engine behavior
- cache/vault behavior
- slang/normalization helpers
- telemetry and license logic
- clipboard pipeline

Recent execution status in this workspace:
- 9/9 tests passed via `tests/run_all.py`.

Gap observation:
- Most automated checks are core-centric; interactive UI end-to-end validation remains partly manual (expected for desktop GUI apps).

## 10. Security, Privacy, and Operational Notes

Privacy profile:
- Telemetry is local-file based by default in this codebase structure.
- Runtime state/config are persisted in local JSON assets.

Operational safeguards:
- Fallback paths for missing model assets through downloader.
- Defensive startup sequencing and logging.

Potential sensitivities:
- Clipboard access and global hotkeys may require permissions/OS compatibility handling.
- First-run model download size can affect onboarding reliability.

## 11. Strengths

- Clear module boundaries and maintainable structure.
- Practical production path for Windows desktop release.
- Strong core-behavior test discipline.
- Real-time UX focus with caching and normalization.
- Automated release script now available for reproducibility.

## 12. Risks and Technical Debt Areas

- Large model distribution burden on first run.
- Desktop UI regression risk without broader automated UI tests.
- Potential fragility around hotkey/clipboard behavior across constrained environments.
- Multiple `.spec` variants can drift if not regularly synchronized.

## 13. Recommendations (Prioritized)

1. Add a lightweight smoke-test harness for post-install launch and first translation event.
2. Add model integrity checks + clearer retry UX for download/conversion failures.
3. Introduce CI artifact checks for EXE/installer metadata consistency.
4. Standardize shared packaging options across all `.spec` variants.
5. Expand telemetry (still local) with release diagnostics toggles for supportability.

## 14. Final Assessment

BabelGG v2 is a mature, structured desktop application codebase with practical release engineering in place. It is suitable for controlled production release, with highest leverage improvements in installer smoke automation, model onboarding robustness, and packaging consistency governance.
