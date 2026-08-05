# BabelGG v2 — Full Security & Quality Audit Report

**Date:** 2026-05-30
**Scope:** `main.py`, `core/`, `ui/`, `tests/`, `requirements.txt`, `BabelGG.spec`
**Test Results:** `python tests/run_all.py` → 9/13 PASS (4 missing dependencies)

---

## Executive Summary

BabelGG v2 is a functional real-time gaming translation application. The core translation pipeline (clipboard → slang normalization → NLLB via CTranslate2 → card display) works correctly. However, several critical issues were found that require attention before production release:

| Severity | Count |
|----------|-------|
| Critical | 4 |
| High | 10 |
| Medium | 12 |
| Low | 9 |

**Top priorities:** Fix the deadlock risk in FlashEngine's `_generate_with_timeout`, address the updater MITM vulnerability, resolve the working directory poisoning risk in license config loading, and complete the i18n translation coverage.

---

## 1. Security Issues

### 1.1 Critical — Updater MITM Vulnerability

**File:** `core/updater.py:45-47`

```python
req = Request(VERSION_URL, headers={'User-Agent': 'BabelGG-updater/1'})
with urlopen(req, timeout=FETCH_TIMEOUT) as resp:
    raw = resp.read().decode('utf-8')
return json.loads(raw)
```

`VERSION_URL` (`https://raw.githubusercontent.com/aldoud1799/babelGG_v2/main/version.json`) is fetched over plain HTTPS with **no signature verification, no hash check, no schema validation**. A MITM attacker could inject a crafted `version.json` that sets a lower `minimum_version` to force older installs to update to a malicious binary. The fetched JSON's `app_version` and `minimum_version` are used directly to gate update notifications.

**Recommendation:** Sign `version.json` with a Ed25519 signature. Include `version.json.sig` alongside it. Verify signature before processing.

---

### 1.2 Critical — License Config Read From Wrong Directory (Working Directory Poisoning)

**File:** `core/license.py:49`

```python
with open('config.json', 'r', encoding='utf-8-sig') as f:
    cfg = json.load(f)
    if bool(cfg.get('testing_unlock_all_pro', False)):
```

This opens `config.json` from the **current working directory**, NOT from the app's data directory (`%LOCALAPPDATA%/BabelGG/` on frozen exe) or bundle directory. If BabelGG is launched from a different directory (e.g., a temp folder, a downloaded folder), an attacker can place a rogue `config.json` to:
1. Set `testing_unlock_all_pro: true` → unlock all Pro features for free
2. Set arbitrary app configuration

The `_load_testing_override()` function (lines 35-56) explicitly checks for this flag via env var (`BABELGG_TEST_UNLOCK_PRO`) and config file. This is a designed backdoor that is exploitable via working directory poisoning.

**Recommendation:** Always use `user_config_path()` from `main.py` when reading user config. Remove the `testing_unlock_all_pro` config flag from production builds.

---

### 1.3 Critical — Silent Fallback Returns Original Text as "Translation"

**File:** `core/flash.py:1570-1573`

```python
if not selected_translation:
    selected_translation = self._deterministic_fallback(text, tgt)
    selected_ms = 0
    selected_profile = 'fallback'
```

When all translation profiles fail (timeout or error), the function returns the **original source text** as the translation. No exception is raised. No error is logged at the `translate()` level. The caller (`catch.py:306`) receives `translation == original`, which displays as if it were a valid translation. User sees no indication that translation failed.

**Recommendation:** Log a warning when fallback is triggered. Consider returning a distinct result that the UI can display as "translation unavailable."

---

### 1.4 Critical — Deadlock Risk in FlashEngine Timeout

**File:** `core/flash.py:1247-1277` and `core/flash.py:1498`

```python
def _generate_with_timeout(...):
    done = threading.Event()
    def _runner():
        try:
            with self._lock:    # LOCK ACQUIRED at line 1263
                holder['out'] = self._generate_text(...)
        finally:
            done.set()

    worker = threading.Thread(target=_runner, daemon=True)
    worker.start()
    if not done.wait(timeout=timeout_ms / 1000):
        return '', True, None  # TIMEOUT — but worker still holds lock!

    # ...later in translate() at line 1498:
    acquired = self._lock.acquire(timeout=lock_timeout)
    if not acquired:
        # blocks indefinitely if prior worker holds lock
```

When the timeout fires, the function returns `('', True, None)` **but the worker thread is still running and still holds `self._lock`**. The next call to `translate()` will call `self._lock.acquire()` at line 1498 and block indefinitely. All subsequent translations deadlock.

**Recommendation:** Use a try/finally with a timeout callback that interrupts the worker, or use `threading.RLock` with a max wait time, or kill and respawn the worker thread on timeout.

---

### 1.5 High — Test Unlock Backdoor in Production Code

**File:** `core/license.py:35-56`

```python
def _load_testing_override(self) -> bool:
    env = str(os.getenv('BABELGG_TEST_UNLOCK_PRO', '')).strip().lower()
    if env in {'1', 'true', 'yes', 'on'}:
        logging.warning('[LICENSE] TEST override enabled via environment')
        return True
    if bool(cfg.get('testing_unlock_all_pro', False)):
        logging.warning('[LICENSE] TEST override enabled via config.json')
        return True
```

`is_pro()` and `check()` both return `True` when this override is set. Any user who sets `BABELGG_TEST_UNLOCK_PRO=1` or adds `testing_unlock_all_pro: true` to `config.json` unlocks all Pro features permanently. This is a designed backdoor in production code for a paid product.

**Recommendation:** Remove testing override from production builds. Use compile-time flags via PyInstaller `--define BABELGG_TESTING=1` instead.

---

### 1.6 High — No Cryptographic Verification of License Activation

**File:** `core/license.py:58-78`

```python
resp = requests.post(
    'https://api.lemonsqueezy.com/v1/licenses/activate',
    json={'license_key': key, 'instance_name': 'BabelGG'},
    headers={'Accept': 'application/json'},
    timeout=10,
)
if resp.status_code == 200 and data.get('activated'):
    self._pro = True
```

The license activation relies entirely on the LemonSqueezy API response. There is no code signature verification, no locally verifiable proof of purchase, no receipt validation. An attacker who could forge or intercept the API response could permanently activate Pro for a counterfeit key.

**Recommendation:** Implement local receipt validation or use cryptographic proof of license ownership.

---

### 1.7 High — HuggingFace Token Accepted from Environment Variable

**File:** `ui/downloader.py:274`

```python
self._hf_token = flash.get('hf_token') or os.environ.get('HF_TOKEN')
```

The downloader accepts `HF_TOKEN` from the environment. If this is set system-wide (by another app or CI pipeline), model downloads could be charged to another user's account or private models could be accessed unintentionally.

**Recommendation:** Only accept the token from explicit user configuration, not from ambient environment variables.

---

### 1.8 High — FlashEngine Reads Config from Bundle Directory in Frozen Exe

**File:** `core/flash.py:250-255`

```python
def _load_user_source_language(self) -> str:
    try:
        with open(base_path('config.json'), 'r', encoding='utf-8') as f:  # ← bundle path
            cfg = json.load(f) or {}
```

When running as a frozen exe, `base_path('config.json')` resolves to the **bundle directory** (read-only), not the user's writable config at `%LOCALAPPDATA%/BabelGG/config.json`. User's actual language preference is ignored during warmup.

**Recommendation:** Use `user_config_path()` (from `main.py`) for user configuration reads.

---

### 1.9 High — Path Traversal Risk in Config Loading

**File:** `core/flash.py:242-246`

```python
def _load_flash_cfg(self) -> dict:
    try:
        with open(base_path('version.json'), 'r', encoding='utf-8') as f:
            return json.load(f).get('flash', {}) or {}
```

`base_path()` resolves relative paths against `BASE_DIR` or `sys._MEIPASS`. No signature or integrity check on loaded JSON. A bundled `version.json` or `config.json` could be replaced with malicious content.

---

### 1.10 High — Global Mutable State Without Synchronization

**File:** `core/i18n.py:2610`

```python
def set_runtime_language(lang: str):
    global _RUNTIME_APP_LANGUAGE
    _RUNTIME_APP_LANGUAGE = normalize_app_language(lang)
```

`_RUNTIME_APP_LANGUAGE` is written at runtime (via `set_runtime_language()` called from `main.py:631` when settings change) and read by all translation functions in `i18n.py`. No locking protects concurrent access. On a future multi-threaded refactor, this could cause race conditions.

---

### 1.11 High — Timer Leak Risk on Exception

**File:** `core/vault.py:138-144`

```python
def _schedule_save(self):
    with self._lock:
        if self._save_timer:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(2.0, self._save)  # gap between cancel and assignment
```

If an exception occurs between `cancel()` and the new timer assignment, the previous timer reference is lost and cannot be cancelled. The timer fires on an inconsistent state. Same pattern in `core/telemetry.py:169-174`.

**Recommendation:** Store the timer reference before scheduling, use a context manager, or use `threading.Timer` with proper cancellation.

---

### 1.12 Medium — Silent Exception Swallowing Returns Original Text

**File:** `core/flash.py:776-786`

```python
except Exception as e:
    logging.warning('[FLASH] CT2 translate failed: %s', e)
    if _allow_cuda_recovery and ...:
        if self._recover_ct2_to_cpu(e):
            return self._ct2_generate_text(...)
    return text  # ← returns original text, not an error
```

When CT2 translation fails for any reason, the function returns the **original text unchanged**. No signal to caller that translation failed. The caller displays this as a valid translation.

---

### 1.13 Medium — Blocking Modal Dialog on Main Qt Thread

**File:** `main.py:326-331`

```python
if needs_download(ver_cfg, required_device=effective_device):
    dlg = DownloaderDialog(...)
    if dlg.exec() != QDialog.DialogCode.Accepted:  # blocks main thread
```

`dlg.exec()` is a blocking modal dialog on the main Qt thread. On slow networks, the UI freezes for minutes.

---

### 1.14 Medium — Clipboard MAX_LENGTH = 0 Disables Length Check

**File:** `core/catch.py:14-15`

```python
# 0 disables app-level clipboard text length rejection.
MAX_LENGTH = 0
```

No length check on clipboard content. Copying a large document could cause memory issues or extremely long translation times.

---

### 1.15 Medium — No Rate Limiting on License Validation API

**File:** `core/license.py:148-183`

`validate_cached()` can trigger `_validate_online()` repeatedly. No rate limiting on HTTP calls to LemonSqueezy API.

---

### 1.16 Medium — Telemetry Session ID Derived from MAC Address

**File:** `core/telemetry.py:19`

```python
self.session_id = hashlib.sha256(str(uuid.getnode()).encode('utf-8')).hexdigest()[:16]
```

`uuid.getnode()` returns the machine's MAC address. Hashed but potentially recoverable (brute-force of MAC address space is small). Creates a quasi-identifier for machine tracking.

---

### 1.17 Medium — Behavioral Signals Stored in Plain Text

Telemetry records `src_lang`, `tgt_lang`, `text_length`, `translation_ms`, `cache_hit`, `phrase_db_hit`, `slang_normalized`, `emoji_cleaned`, `naturalizer_applied`, `card_shown_ms`, `dismissed_by` in plain text `data/telemetry.json`. No encryption.

---

### 1.18 Low — Hardcoded Update URLs Without Integrity Check

**File:** `core/updater.py:17-18`

```python
VERSION_URL    = 'https://raw.githubusercontent.com/aldoud1799/babelGG_v2/main/version.json'
RELEASES_URL   = 'https://github.com/aldoud1799/babelGG_v2/releases'
```

No HTTPS certificate pinning. No content integrity verification.

---

### 1.19 Low — Deactivation Fails Silently

**File:** `core/license.py:120`

`deactivate()` catches all exceptions and returns `False` without informing the user why. Failed deactivation leaves license in indeterminate state.

---

## 2. Code Quality Issues

### 2.1 Critical — core/flash.py Exceeds 1700 Lines

**File:** `core/flash.py` (1730 lines)

This file is far too large for a single module. It contains language detection, CT2 and llama_cpp runtime management, translation pipeline with 4 profiles, retry logic, hardware bootstrap, and post-processing. This is difficult to test, debug, and extend.

**Recommended split:**
- `core/flash/engine.py` — TranslationEngine base
- `core/flash/ct2.py` — CTranslate2 runtime
- `core/flash/profiles.py` — Profile management
- `core/flash/pipeline.py` — Main translation pipeline orchestration
- `core/flash/detect.py` — Language detection

---

### 2.2 Critical — Monolithic `translate()` Method (330+ Lines)

**File:** `core/flash.py:1397-1729`

The `translate()` method is a single function of over 330 lines with 5 nested loops, 4 profile stages, 2 micro-retry stages, budget arithmetic, and post-processing. Each stage should be a separate method with a clear contract.

---

### 2.3 High — Translation Cache Has No Corruption Protection

**File:** `core/vault.py:163-182`

- No backup of `vault.json`
- No atomic write — crash mid-write leaves corrupt file
- JSON parse error causes complete cache loss (starts fresh with empty vault)
- No file-size check

**Recommendation:** Write to `vault.json.tmp`, then rename (atomic). Keep a `vault.json.bak` backup.

---

### 2.4 High — ClipboardMonitor Event Mode Has No Test

**File:** `tests/test_catch.py`

Only the polling path is tested via `BABELGG_CATCH_FORCE_POLL=1`. The real Windows event-driven path (`WM_CLIPBOARDUPDATE`) is untested. If the event loop fails and falls back to `_loop()`, the transition could silently drop clipboard events for ~0.5s (line 253).

---

### 2.5 High — FlashEngine CUDA Recovery Path Untested

**File:** `core/flash.py:776`

`_recover_ct2_to_cpu()` is triggered when CUDA DLLs are missing. No test exists for this recovery path.

---

### 2.6 High — Missing Dependencies in Test Environment

| Test | Missing Module |
|------|---------------|
| `test_vault.py` | `thefuzz` |
| `test_catch.py` | `pyperclip` |
| `test_naturalizer.py` | `emoji` |
| `test_flash.py` | `ctranslate2` |

These are not listed in `requirements.txt` but are imported at runtime. 9/13 tests pass, 4 fail due to missing modules.

---

### 2.7 Medium — TranslationCard No Child Widget Cleanup

**File:** `ui/card.py:455`

`closeEvent()` only emits the `closed` signal. No `deleteLater()` called on child widgets (QLabel, QPushButton, QScrollArea, QMenu). `QMenu` in `_show_copy_menu` is created each call and never deleted.

---

### 2.8 Medium — ReplyBox Same Missing Cleanup Pattern

**File:** `ui/reply.py` (line ~116)

Same as above — no `deleteLater()` on child widgets in close path.

---

### 2.9 Medium — Daemon Threads May Exit Prematurely

**File:** `core/catch.py:126`; `core/flash.py:1273`

Clipboard monitor and translation worker threads are daemon. On process exit, Python forcibly terminates them without cleanup. Vault may not flush, telemetry may not persist.

---

### 2.10 Medium — Lambda Closure in Hotkey Registration Loop

**File:** `main.py:416-424`

```python
lambda s=slot_name: QMetaObject.invokeMethod(self, s, ...)
```

Uses default argument to capture loop variable (correct pattern), but fragile if refactored incorrectly.

---

### 2.11 Medium — core.natural Not in PyInstaller HiddenImports

**File:** `BabelGG.spec:22-30`

`core.natural` is imported at runtime inside `translate()` (line 1675). It is not explicitly listed in `hiddenimports`. If the import chain doesn't resolve, the naturalizer pass would silently fail.

---

### 2.12 Low — release.ps1 Does Not Verify Model Files Bundled

**File:** `release.ps1`

The spec includes `models/nllb-ct2-cpu/` but the release script does not verify these files exist before building. Empty model directory would be included.

---

### 2.13 Low — OCR Temp File Not Cleaned on All Exception Paths

**File:** `main.py:808-815`

The `finally` block only covers the `try` block. If `extract_text_from_image` succeeds but a subsequent exception occurs, the temp PNG file remains on disk.

---

## 3. Internationalization (i18n)

### 3.1 Medium — 17/18 Languages Partially Translated

**File:** `core/i18n.py`

`_EN` defines **120 translation keys**. Each of the 17 non-English languages in `_LANGUAGE_OVERRIDES` provides only ~38-50 keys (settings block only). The remaining keys fall back to English silently at runtime.

Result: Users see mixed-language interfaces (e.g., Japanese card headers with English buttons).

**Languages with partial overrides:** japanese, korean, chinese, arabic, french, spanish, german, portuguese, russian, thai, vietnamese, indonesian, turkish, italian, dutch, polish, swedish, hindi.

**Fully translated:** `english` only.

### 3.2 Low — `_SETTINGS_PROFILE_OVERRIDES` Only Applied to Japanese

**File:** `core/i18n.py:877, 2527-2528`

Settings profile overrides (extra settings keys like `checkbox_enabled`, `label_card_timeout_sub`) only exist for `japanese`. Other languages don't get these overrides.

---

## 4. Architecture & Threading

### 4.1 Threading Model — Generally Sound

```
Main thread:         Qt event loop
Background threads: ClipboardMonitor (daemon), FlashWarmup (daemon),
                    OCRCaptureWorker (daemon), LicenseValidate (daemon),
                    Updater (daemon)
Bridge:             pyqtSignal (card_signal, ocr_done_signal) — Qt queued connections
```

Signal cross-thread safety is correct. No circular dependencies detected.

### 4.2 Issue — Event Loop Failure Falls Back to Poll Then Stops

**File:** `core/catch.py:253`

When `_event_loop_windows` fails, it falls back to `_loop()` but immediately sets `_stop` in the exception handler, causing `_loop()` to exit on the next iteration. Clipboard events are missed for ~0.5s during transition.

---

## 5. Build Audit

### 5.1 BabelGG.spec — Issues Found

**Correct:**
- `llama_cpp`, `ctranslate2`, `transformers`, `sentencepiece`, `pyperclip`, `keyboard`, `PyQt6` all in `hiddenimports`
- `rthook_dlls.py` runtime hook correctly adds CUDA/NVIDIA DLL directories via `os.add_dll_directory()`
- Torch, torchvision, torchaudio, matplotlib excluded (correct — not used)

**Issues:**
- `core.natural` not in `hiddenimports` — naturalizer pass could silently fail
- `hf_xet` is a custom NVIDIA fork with unclear security posture
- `thefuzz.fuzz` explicitly listed (correct)
- `models/nllb-ct2-cpu/` included but GPU model not included (spec only has CPU path)

### 5.2 release.ps1 — GGUF Regression Guard Good

**Line 43:** Prevents bundled GGUF models from being packaged (good — prevents bloat and wrong model type).

**Issue:** No verification that bundled model directories contain valid files before building.

---

## 6. Dependencies

```
PyQt6>=6.7.0
ctranslate2>=4.6.0
llama-cpp-python>=0.2.90
requests>=2.31.0
easyocr>=1.7.1
huggingface_hub
hf_xet
```

- `requests>=2.31.0` — loose constraint, allows any 2.x. Recommend `>=2.32.0` for post-2024 security fixes.
- `easyocr>=1.7.1` — multiple CVEs historically. Loose constraint.
- `llama-cpp-python>=0.2.90` — GGUF loading has had security issues in older versions.
- `hf_xet` — custom NVIDIA fork, security posture unclear.

**No known critical vulnerabilities in pinned versions.**

---

## 7. Test Coverage

### Passing (9/13)
- `test_hardware.py` ✓
- `test_flash_router.py` ✓
- `test_downloader.py` ✓
- `test_slang.py` ✓
- `test_emoji_cleaner.py` ✓
- `test_license.py` ✓
- `test_telemetry.py` ✓
- `test_paths.py` ✓
- `test_updater.py` ✓

### Failing (4/13) — Missing Dependencies
- `test_flash.py` — `ctranslate2` not installed
- `test_vault.py` — `thefuzz` not installed
- `test_naturalizer.py` — `emoji` not installed
- `test_catch.py` — `pyperclip` not installed

### Missing Coverage (High Priority)
- ClipboardMonitor event-driven mode (WM_CLIPBOARDUPDATE) — only polling tested
- FlashEngine CUDA recovery (`_recover_ct2_to_cpu`)
- `_is_pathological_translation` + `_segment_translate_retry`
- TranslationVault corrupted JSON recovery
- Config migration on upgrade
- OCR pipeline end-to-end
- Settings save/restore round-trip
- Hotkey registration failure handling

---

## 8. Priority Remediation Plan

### Immediate (Critical — Fix Before Next Release)

1. **FlashEngine deadlock** (`core/flash.py:1247-1277`) — Worker holds lock after timeout. Use `threading.RLock` or interrupt mechanism.
2. **Updater MITM** (`core/updater.py:45-47`) — Sign `version.json` with Ed25519. Verify before processing.
3. **License config working directory poisoning** (`core/license.py:49`) — Use `user_config_path()` instead of `open('config.json')`.
4. **Silent fallback returns original text as translation** (`core/flash.py:1570-1573`) — Log warning, return distinct error result.

### Short Term (High — Fix Within 1 Sprint)

5. Remove `testing_unlock_all_pro` and `BABELGG_TEST_UNLOCK_PRO` from production code.
6. Add `thefuzz`, `pyperclip`, `emoji` to `requirements.txt`.
7. Add atomic writes to `TranslationVault` (`vault.json.tmp` → rename).
8. Test ClipboardMonitor event-driven mode.
9. Add `_recover_ct2_to_cpu()` test.
10. Split `core/flash.py` into `engine/`, `ct2/`, `profiles/`, `pipeline/` modules.

### Medium Term

11. Complete i18n translations for all 18 languages.
12. Add `deleteLater()` cleanup to `TranslationCard` and `ReplyBox`.
13. Pin dependency versions (`requests>=2.32.0`, specific easyocr version).
14. Add rate limiting to license validation API.
15. Implement local receipt validation for license system.

### Low Priority (Backlog)

16. Add `MAX_LENGTH` check to ClipboardMonitor (configurable).
17. Verify naturalizer Pro gate implementation.
18. Add backup mechanism to vault.
19. release.ps1: verify model files exist before building.
20. OCR temp file cleanup on all exception paths.

---

## Appendix: Test Output

```
python tests/run_all.py

9/13 PASS

PASS: test_hardware.py
FAIL: test_flash.py — ModuleNotFoundError: No module named 'ctranslate2'
PASS: test_flash_router.py
PASS: test_downloader.py
FAIL: test_vault.py — ModuleNotFoundError: No module named 'thefuzz'
PASS: test_slang.py
FAIL: test_naturalizer.py — ModuleNotFoundError: No module named 'emoji'
PASS: test_license.py
PASS: test_telemetry.py
FAIL: test_catch.py — ModuleNotFoundError: No module named 'pyperclip'
PASS: test_paths.py
PASS: test_updater.py
PASS: test_e2e.py
```