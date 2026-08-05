# RULES.md — BabelGG v2

These are non-negotiable. Violating any of these causes crashes, data corruption, or silent failures. Read every rule before touching any file.

---

## Rule 1 — Threading (violation = ANR or crash)

All blocking work (FlashEngine translate, OCR, clipboard polling, license validation) runs on background daemon threads. The Qt event loop runs on the main thread. UI updates only on the main thread via `pyqtSignal`.

```
Background thread: result = flash.translate(text, tgt)
Main thread:       card_signal.emit(result) → _show_card() updates UI
```

If you are about to put any of the following on the main thread, stop:
- Translation calls (`flash.translate()`)
- Clipboard read/write (`pyperclip.paste()`, `catch.ignore_once()`)
- OCR processing (`ocr.extract_text_from_image()`)
- File I/O in the data directory (vault, telemetry, phrases)
- Network requests (updater version check, license validation)

---

## Rule 2 — Core stability (violation = silent failures)

**Do not modify `core/flash.py` (70k+ lines) or `core/vault.py` unless the task explicitly and specifically requires it.** These files are intentionally large and have been iteratively tuned for translation quality and cache reliability.

If you think something looks wrong or improvable — read `_ai/DECISIONS.md` before touching anything.

---

## Rule 3 — Path resolution (violation = crash or missing data on frozen exe)

Path resolution differs between source and frozen exe:
- **Source**: `BASE_DIR = os.path.dirname(os.path.abspath(__file__))`, `USER_DATA_ROOT = BASE_DIR`
- **Frozen exe**: `BASE_DIR = os.path.dirname(sys.executable)`, `USER_DATA_ROOT = LocalAppData/temp`

Always use the path helpers in `main.py`: `app_path()`, `data_path()`, `user_config_path()`, `asset_path()`. Never hardcode paths.

---

## Rule 4 — Data mutation (violation = cache corruption or telemetry loss)

- `TranslationVault` writes are buffered and flushed on `flush()` or app quit. Always call `flush()` before exit.
- Telemetry is buffered and flushed via `telemetry.flush()`. Call before quit.
- Clipboard ignore list (`catch.ignore_once`) is surgical — one-shot, not a rescan.

---

## Rule 5 — Lifecycle / context rule (violation = crash)

`BabelGG` object owns all subsystems. On `_quit()`:
1. `catch.stop()` — stop clipboard monitor
2. `vault.flush()` — persist cache
3. `telemetry.flush()` — persist telemetry
4. `_release_instance_lock()` — unlock single-instance lock

Always clean up in this order.

---

## Rule 6 — Testing (violation = shipping broken builds)

Run all test suites before marking any task done.

- `python tests/run_all.py` — core suite, expected 10/10 PASS
- `python tests/run_all.py --extended` — includes language matrix (known acceptable failures in specific language pairs)

---

## Quality gates — task is not done until all pass

- [ ] `pyinstaller BabelGG.spec --clean` succeeds
- [ ] `python tests/run_all.py` — 10/10 PASS
- [ ] No crashes at runtime
- [ ] Translation latency < 2s on target hardware (CPU mode)