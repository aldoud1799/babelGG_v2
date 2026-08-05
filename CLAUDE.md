# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Startup — always read these first (in order)

1. `_ai/RULES.md` — threading, core stability, file ops. Non-negotiable.
2. `_ai/ARCHITECTURE.md` — system map, data flow, key files.
3. `_ai/SESSION_HANDOFF.md` — last session state (unreliable if >3 days old).

**Current handoff date:** 2026-05-30 — verify with user before trusting if stale.

---

## Project identity

BabelGG v2 — Real-time gaming translation: copy foreign text → floating card in ~1 second. Core design: **latency over cache fidelity** (cache disabled by default).

| | |
|---|---|
| Language | Python 3.x |
| Min/Target | Windows 11, PyInstaller frozen exe |
| Package / ID | BabelGG (`SetCurrentProcessExplicitAppUserModelID('BabelGG')`) |
| Core | NLLB-200-distilled-600M via CTranslate2 (`alirezamsh/small100`) |
| Test device / env | Windows 11 Pro, CPU primary, CUDA GPU when available |

---

## Council Protocol

Required before: new features, changes touching >2 files, changes to `core/flash.py`, `core/vault.py`, core/engine changes.

1. Propose approach → 2. Critique it (what could go wrong) → 3. Revise → 4. Implement

Skip for single-file, single-function fixes.

---

## Common commands

```
# Install / first run
pip install -r requirements.txt && python download_models.py && python main.py

# Build frozen exe
pyinstaller BabelGG.spec --clean

# Logs
Get-Content data\babelgg.log -Wait -Tail 50

# Tests
python tests/run_all.py          # core suite — 10/10 PASS expected
python tests/run_all.py --extended  # language matrix

# Release build (exe + Inno Setup installer)
.\release.ps1
.\release.ps1 -SkipTests
```

---

## Quality gates — task is not done until all pass

- `pyinstaller BabelGG.spec --clean` succeeds
- `python tests/run_all.py` — 10/10 PASS
- No crashes at runtime
- Translation latency < 2s on CPU for typical gaming text

---

## When to load additional docs

- `_ai/DECISIONS.md` — if touching `core/flash.py`, `core/vault.py`, `core/catch.py`, threading model, or anything that looks "wrong." Read before deciding to change it.
- `_ai/BUILD.md` — full build/test/device setup details.
- `main.py` — always read when coordinating across subsystems (signals, paths, lifecycle).

---

## Code philosophy

- **No bloat.** Every addition must earn its place.
- **Cache off by default.** Fresh LLM inference on every translate — this is intentional.
- Prefer readable, direct code over clever abstractions.
- If a fix feels hacky, stop and ask before proceeding.
- `core/flash.py` (~1700 lines) and `core/i18n.py` (~4500 lines) are intentionally large and stable — do not split or refactor them.

---

## Key architectural points

### Threading model
```
Background threads: ClipboardMonitor, FlashWarmup, OCRCaptureWorker, LicenseValidate, Updater
Main thread: Qt event loop
Bridge: pyqtSignal (card_signal, ocr_done_signal)
```

### Path resolution
Frozen exe uses `sys._MEIPASS` for bundled assets. Always use `app_path()`, `data_path()`, `asset_path()` — never hardcode.

### Data flow
```
ClipboardMonitor → slang.py → FlashEngine.translate() → [vault cache] → card_signal.emit()
                                                                              ↓
OCRSelectionOverlay → OCRReader.extract_text_from_image() → FlashEngine.translate() → card_signal.emit()
```

### Lifecycle cleanup order (on quit)
`catch.stop()` → `vault.flush()` → `telemetry.flush()` → `_release_instance_lock()` → `QApplication.quit()`

---

## Session handoff

At the end of every session, before saying anything else, update `_ai/SESSION_HANDOFF.md` with what you did, files changed, test results, and what's incomplete. This is mandatory.