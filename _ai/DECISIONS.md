# DECISIONS.md — BabelGG v2

This file explains why the code is the way it is. Before "fixing" anything that looks wrong or improvable, read the relevant entry here. Many decisions that look like mistakes are intentional.

---

## Decision 1 — Translation cache disabled by default

**What:** `translation_cache_enabled=False` in default config. `TranslationVault` is not instantiated unless user explicitly enables it.

**Why:** The primary design goal is translation *quality*, not throughput. Cache pollution (wrong translations cached for similar text) was observed in testing when cache was enabled by default. Users gaming real-time need accuracy on first translation, not cached stale results. Cache is still available as an opt-in for users who prefer speed over fidelity.

**Do not change this.** The default will remain disabled. If you want to re-evaluate, run A/B testing with real users and measure translation error rates, not just latency.

---

## Decision 2 — NLLB-200-distilled-600M over llama.cpp GGUF

**What:** Translation engine uses `alirezamsh/small100` (NLLB distilled, 600M params) via CTranslate2, not a llama.cpp GGUF model.

**Why:** NLLB was specifically trained for multilingual translation quality. The distilled version maintains quality while reducing size. CTranslate2 provides efficient CPU/GPU execution with quantization. llama.cpp models tested had inferior translation quality for gaming slang, especially for CJK languages.

**Do not change this** unless you run a full translation quality benchmark (BLEU, CometKiwi) against 1000+ gaming text samples with both approaches.

---

## Decision 3 — ClipboardMonitor starts only after FlashEngine ready

**What:** `catch.start()` is called inside `_warm_flash()` after `self.flash.ready == True`.

**Why:** Prevents premature clipboard polling and cache pollution before the translation engine is available. If clipboard monitoring starts before flash is ready, copied text would be lost or processed against a non-ready engine.

**Do not change this.**

---

## Decision 4 — Fuzzy matching threshold 96 with 18-char minimum

**What:** `TranslationVault.FUZZY_THRESHOLD=96`, `MIN_FUZZY_CHARS=18`, `MAX_FUZZY_LEN_DRIFT=0.25`.

**Why:** Threshold 96+ is strict enough to avoid false positives on gaming text that legitimately varies (e.g., "gg wp" vs "ggwp"). 18-char minimum prevents short strings (which have high collision rates) from triggering fuzzy match. 25% length drift prevents comparing completely different texts.

**Do not change this** unless you observe systematic false positive cache hits in gaming text.

---

## Decision 5 — Multi-hotkey registration with cooldown

**What:** Each hotkey action (reply, settings, toggle, OCR) registers multiple key combinations: primary (`ctrl+shift+r`), near-hand fallback (`alt+r`), legacy fallback (`f8`). Hotkey handler has 0.9s cooldown to prevent duplicate firing.

**Why:** Games often swallow Ctrl+Shift combos. Having near-hand (Alt+R) and legacy (F8) fallbacks ensures reliability. Cooldown prevents the multi-registration from firing the action multiple times on a single press.

**Do not change this.** If you find a better approach, it must maintain the multi-fallback strategy.

---

## Decision 6 — Path resolution via `_resource_path()` with MEIPASS fallback

**What:** All path resolution uses `app_path()`, `data_path()`, `asset_path()` which call `_resource_path()`. This checks both `BASE_DIR` and `sys._MEIPASS` (PyInstaller temp directory) for bundled resources.

**Why:** Frozen exe files extract bundled assets to `sys._MEIPASS` at runtime, not alongside the executable. The dual-check ensures assets (icons, phrases.json, version.json) load correctly in both source and frozen modes.

**Do not change this.** If you need a new resource path, add a new helper that follows the same pattern.

---

## Decision 7 — Single-instance lock via msvcrt locking on file handle

**What:** `_acquire_single_instance_lock()` uses `msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)` to acquire a non-blocking exclusive lock on a file in `data_path()`.

**Why:** Windows file locking with `msvcrt` is reliable across all Windows versions and doesn't require admin rights. Alternative approaches (mutex, semaphore) either require admin or have issues with GUI app instances.

**Do not change this** unless you find a Windows-version-compatible approach that doesn't require admin.

---

## Decision 8 — OCR garbled-text gate in pipeline, not backend

**What:** `OCRReader.is_likely_garbled()` is called in `_run_ocr_pipeline()` (app layer) after `extract_text_from_image()`, not inside the OCR backend.

**Why:** Prevents duplicating the filter across OCR backends. Centralizes the rejection policy in one place. If the OCR result looks noisy, the user gets specific feedback ("Crop a bit wider and keep text high-contrast") instead of silent failure.

**Do not change this.**

---

## Decision 9 — Settings changes apply live via hotkey re-registration

**What:** `_open_settings()` saves new config, then calls `self._register_hotkeys()` which removes all hotkeys and re-registers them.

**Why:** Without re-registration, hotkey changes would require app restart. The `keyboard.remove_hotkey()` approach works reliably for the keyboard library being used.

**Do not change this.**

---

## Decision 10 — Pro license feature gates in ui layer, not engine

**What:** License checks (`license.check('history')`, `license.check('ocr')`) live in the UI handlers (`_open_history()`, `_do_ocr()`) in `main.py`, not in the translation engine or clipboard monitor.

**Why:** Keeps the core translation pipeline free of license logic. Pro features are UI-level upsells. The translation engine doesn't care about license state.

**Do not change this.**