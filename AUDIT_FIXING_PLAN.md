# BabelGG v2 — Audit Fixing Plan

**Audit date:** 2026-05-30
**Total findings:** 35 (4 Critical, 10 High, 12 Medium, 9 Low)
**Applies to:** BabelGG v2 at D:\AbeSoft\BabelGG_v2

---

## Phase 1: Critical Fixes (Before Next Release)

### 1.1 FlashEngine Deadlock — `_generate_with_timeout` timeout worker holds lock

**Root cause:** `_generate_with_timeout()` at `core/flash.py:1247` spawns a worker that acquires `self._lock` then waits for `done.wait(timeout)`. When timeout fires, the function returns `('', True, None)` but the worker thread is still running and still holds the lock. Subsequent `translate()` calls block indefinitely at `self._lock.acquire()` (line 1498).

**Fix approach:**
- Replace `threading.Event` wait with a bounded wait + `threading.RLock` that can be released from the main thread
- On timeout: set a flag that worker checks before acquiring lock, then join worker with short timeout
- If worker still holds lock after join, spawn a new FlashEngine instance rather than leaking the locked instance

**Files to modify:** `core/flash.py` (lines ~1247-1277, ~1498)

**Verification:** Run `python tests/run_all.py` — all 13 should pass. Run 100 rapid translations with timeout=1ms to confirm no deadlock.

---

### 1.2 Updater MITM Vulnerability — `version.json` fetched without integrity check

**Root cause:** `core/updater.py:45-47` fetches `version.json` from GitHub raw over HTTPS with no signature, hash, or schema validation. MITM attacker can inject malicious version to force downgrade.

**Fix approach:**
1. Generate an Ed25519 keypair offline. Embed the **public** key in `core/updater.py` (constant string).
2. After `version.json` is fetched, fetch `version.json.sig` from the same URL (GitHub raw supports raw files).
3. Verify the signature using the embedded public key.
4. If verification fails, log error and skip update check. Do NOT fall back to using the unverified data.
5. Add a schema validator (use `jsonschema` or manual field validation) for `app_version`, `minimum_version`, `flash` dict keys.

**Files to modify:** `core/updater.py`

**Verification:** Temporarily serve a modified `version.json` with lower `minimum_version` — app should log signature verification failure and skip update notification. Does not force downgrade.

---

### 1.3 License Config Working Directory Poisoning

**Root cause:** `core/license.py:49` does `open('config.json')` which reads from the **current working directory**, not the app's data directory. An attacker who can launch BabelGG from a specific directory (e.g., via shortcut, download folder) can place a rogue `config.json` with `testing_unlock_all_pro: true` to unlock Pro features for free.

**Fix approach:**
1. Replace all `open('config.json')` in `core/license.py` with a call to `user_config_path()` from `main.py` path helpers. Since `core/license.py` is a core module and can't import from `main.py` (would be circular), replicate the path logic or accept `config_path` as a constructor argument.
2. Remove `testing_unlock_all_pro` from `LicenseManager` entirely — it should not exist in production code. If testing builds need a different approach, use a compile-time PyInstaller `--define` flag that sets a C preprocessor macro at build time.
3. Remove `BABELGG_TEST_UNLOCK_PRO` env var check from `_load_testing_override()`.

**Files to modify:** `core/license.py` (remove testing backdoor, fix config path), `core/flash.py` (fix `_load_user_source_language` to use correct config path too)

**Verification:** Create a `config.json` with `testing_unlock_all_pro: true` in a random directory, launch the app from that directory — Pro features should NOT be unlocked.

---

### 1.4 Silent Fallback Returns Original Text as "Translation"

**Root cause:** `core/flash.py:1570-1573` — when all profiles fail, `_deterministic_fallback` is called which returns the source text if no phrase match exists. No error is logged at the `translate()` level, and the result dict shows `translation == original`, which displays as if it were a valid translation.

**Fix approach:**
1. In `_deterministic_fallback()`, if no phrase match found, return a sentinel value (e.g., `None` or a distinct string like `"[TRANSLATION_FAILED]"`) instead of returning the original text.
2. In `translate()`, when `selected_translation` is falsy after all profiles and fallback, log a warning: `logging.warning('[FLASH] All profiles failed for input: %s', text[:50])`.
3. Return `None` from `translate()` when translation completely fails. Caller (`catch.py:306`) already checks `if result:` but only logs — it should also show a "translation unavailable" card or a status message.
4. Add a new result key `translation_failed: True` to the result dict so the UI can display appropriate messaging.

**Files to modify:** `core/flash.py` (lines ~1384-1390, ~1570-1573), `core/catch.py` (line ~306)

**Verification:** With no model loaded, copy foreign text — should show error card or "unavailable" message, NOT the original text as translation.

---

## Phase 2: High Priority Fixes (Within 1 Sprint)

### 2.1 Add Missing Dependencies to requirements.txt

**Fix:** Add to `requirements.txt`:
```
thefuzz
pyperclip
emoji
```

Also pin `ctranslate2>=4.6.0` explicitly (currently present).

**Files to modify:** `requirements.txt`

---

### 2.2 TranslationVault Atomic Writes + Backup

**Root cause:** `core/vault.py` writes directly to `vault.json` with no atomic write, no backup, no corruption protection. Crash mid-write = corrupt file = complete cache loss.

**Fix approach:**
1. Write to `vault.json.tmp` first, then `os.replace()` to `vault.json` (atomic on Windows).
2. Before write, copy existing `vault.json` to `vault.json.bak`.
3. On `_load()`, if `vault.json` is corrupt, try `vault.json.bak` before starting fresh.
4. Add a `_version` field to the vault JSON to allow future schema migrations.

**Files to modify:** `core/vault.py` (lines ~166-182)

---

### 2.3 Fix `_load_user_source_language` to Read User Config

**Root cause:** `core/flash.py:250-255` uses `base_path('config.json')` which resolves to the bundle directory in frozen exe, ignoring the user's actual language preference.

**Fix approach:**
1. `FlashEngine.__init__` receives `user_config_path` as an optional parameter (default to `base_path('config.json')` for backward compatibility in source mode).
2. When frozen (`sys.frozen`), use `user_config_path()` from `main.py` logic (resolve to `%LOCALAPPDATA%/BabelGG/config.json`).
3. Same fix needed for `_load_flash_cfg()` — it reads `version.json` from bundle which is correct (bundled), but the user-facing config read should use user config path.

**Files to modify:** `core/flash.py` (lines ~242-255, ~1397+ init)

---

### 2.4 ClipboardMonitor Event-Driven Mode Test Coverage

**Fix approach:**
1. Add `test_catch_event_mode.py` or extend `test_catch.py` to test the Windows event path.
2. Use `ctypes` to post a `WM_CLIPBOARDUPDATE` message directly to the listener window to simulate clipboard change events.
3. Add `BABELGG_CATCH_FORCE_POLL=0` (or default to event mode) to force event mode in tests.

**Files to modify:** `tests/test_catch.py`

---

### 2.5 FlashEngine CUDA Recovery Test

**Fix approach:**
1. Add test that simulates CUDA error by mocking `_ct2_generate_text` to raise `CUDAError`.
2. Verify `_recover_ct2_to_cpu()` is triggered and device falls back to CPU.
3. Verify subsequent translations work on CPU path.

**Files to modify:** `tests/test_flash.py`

---

### 2.6 Remove `HF_TOKEN` Environment Variable Support

**Root cause:** `ui/downloader.py:274` accepts `HF_TOKEN` from environment, which could inadvertently use another user's account.

**Fix approach:**
1. Remove `os.environ.get('HF_TOKEN')` from the token lookup.
2. Only accept token from explicit config (`flash.get('hf_token')`).
3. If no token available and model requires auth, show user a dialog asking for token.

**Files to modify:** `ui/downloader.py` (line ~274)

---

## Phase 3: Medium Priority

### 3.1 TranslationCard / ReplyBox Child Widget Cleanup

**Fix approach:** In `TranslationCard.closeEvent()`, after emitting the `closed` signal, iterate child widgets and call `deleteLater()`. Same for `ReplyBox`.

**Files to modify:** `ui/card.py` (line ~455), `ui/reply.py` (~line 116)

---

### 3.2 i18n — Complete All 18 Language Translations

**Fix approach:**
1. Add a script to report which keys are missing from each language's override dict.
2. Generate a completion report for each language.
3. Fill in missing translations for all 17 non-English languages.
4. `_SETTINGS_PROFILE_OVERRIDES` should apply to all languages, not just Japanese.

**Files to modify:** `core/i18n.py`

---

### 3.3 Pin Dependency Versions

**Fix approach:**
```
requests>=2.32.0
easyocr>=1.7.1,<2.0
llama-cpp-python>=0.2.90,<1.0
```

**Files to modify:** `requirements.txt`

---

### 3.4 Rate Limit License Validation API

**Fix approach:**
- In `LicenseManager`, add a `_last_validate_ts` and `_validate_interval_s = 3600` (1 hour minimum between online validations).
- If online validation is requested but less than `_validate_interval_s` has passed since last, skip the network call.

**Files to modify:** `core/license.py` (~line 148-183)

---

### 3.5 Add `MAX_LENGTH` Check to ClipboardMonitor

**Fix approach:**
- Make `MAX_LENGTH` configurable via `config.json` (default `0` for backward compat, but warn if > 10000 chars).
- Log when clipboard text exceeds threshold.

**Files to modify:** `core/catch.py` (line ~14-15)

---

## Phase 4: Low Priority (Backlog)

### 4.1 Add `core.natural` to PyInstaller HiddenImports
Fix: Add `'core.natural'` to `hiddenimports` in `BabelGG.spec` to ensure naturalizer pass is not silently excluded.

### 4.2 release.ps1 — Verify Model Files Before Building
Add a check that `models/nllb-ct2-cpu/` directory exists and contains files before building the installer.

### 4.3 Telemetry — Use Random Session ID Instead of MAC Hash
Replace `uuid.getnode()` with `secrets.token_hex(16)` for the session ID.

### 4.4 Daemon Thread Exit — Flush Vault/Telemetry Before Exit
Ensure `atexit` or Qt `aboutToQuit` handler calls `vault.flush()` and `telemetry.flush()` before threads are forcibly terminated.

---

## Verification Plan

After each phase:
1. Run `python tests/run_all.py` — all tests must pass
2. Run `python tests/run_all.py --extended` — language matrix
3. Launch app with `python main.py` (or venv python) — verify startup, tray icon, no errors in log
4. Copy foreign text — verify card appears with translation
5. Check `data/babelgg.log` for any warnings/errors

For critical fixes specifically:
- **Deadlock test:** Set `timeout_ms=1` on a dummy translation loop, run 50 iterations, verify no hang
- **MITM test:** Temporarily serve an altered `version.json` with fake signature, verify app logs error and skips
- **Config poisoning test:** Place rogue `config.json` in a temp directory, launch from that directory, verify no Pro access
- **Fallback test:** With no model, copy text, verify error message not original text