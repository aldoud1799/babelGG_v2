# ARCHITECTURE.md — BabelGG v2

The system map. Read this to understand where things live and how they connect before touching anything.

---

## Core concept

Real-time gaming translation. User copies foreign text → floating card appears within 1 second. The central design decision is **latency over cache fidelity** — translation cache is disabled by default to ensure fresh LLM inference on every translation, not a cached/stale result.

---

## FlashEngine routing table

Adaptive translation engine with four paths. Selection is automatic based on GPU availability and load.

| Component | Version / Config | Handles / Responsibilities |
|-----------|-----------------|---------------------------|
| NLLB-200-distilled-600M | CT2 int8 / int8_float16 | Translation model, 19 target languages |
| Path A | GPU full offload (`n_gpu_layers=-1`) | Best quality, requires CUDA |
| Path B | GPU constrained offload | Reduced layers, CUDA fallback |
| Path C | CPU-safe mode | No GPU available |
| Path D | Deterministic fallback | Returns source text on failure |

**Do not modify `core/flash.py`.** See `_ai/RULES.md` and `_ai/DECISIONS.md` for why.

---

## Data flow

```
User copies text
  → ClipboardMonitor (catch.py, background thread, poll 0.5s)
    → slang.py normalizer (140+ gaming terms, ja/en/ru/ko/zh)
    → FlashEngine.translate() — NLLB via CTranslate2
    → vault.py lookup (if cache enabled) — SHA256 exact + fuzzy match
    → card_signal.emit(result) — thread-safe Qt signal
      → _show_card() on main Qt thread
        → TranslationCard (ui/card.py) — floating card, auto-dismiss, pin, reply

OCR capture (Ctrl+Shift+G)
  → OCRSelectionOverlay (ui/ocr_overlay.py) — fullscreen region select
    → OCRReader (core/ocr.py) — EasyOCR backend
    → flash.translate()
    → same card_signal → TranslationCard

Reply compose
  → ReplyBox (ui/reply.py)
    → flash.translate() with language selector
    → catch.ignore_once() — prevent clipboard loop
```

---

## Key files

| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | ~976 | Entry point, BabelGG class, Qt event loop, signal coordination |
| `core/flash.py` | ~1700 | Translation engine, adaptive routing, post-processing |
| `core/vault.py` | ~170 | LRU translation cache, fuzzy matching, persistence |
| `core/catch.py` | ~400 | Clipboard monitor, dual-mode (pyperclip + Win32 API fallback) |
| `core/i18n.py` | ~4500 | Translations, language profiles, runtime language switching |
| `ui/settings.py` | ~1100 | Settings window, all user preferences |
| `ui/reply.py` | ~700 | Reply compose box |
| `ui/card.py` | ~450 | Floating translation card |

`core/i18n.py` is intentionally large — all UI strings are centralized for translation. Do not split.

---

## Entry points and screen/module structure

```
main.py
  ├── BabelGG class — central coordinator
  │   ├── TrayManager (ui/tray.py) — system tray, hotkeys, status
  │   ├── TranslationCard (ui/card.py) — floating card
  │   ├── ReplyBox (ui/reply.py) — compose + send
  │   ├── SettingsWindow (ui/settings.py) — preferences
  │   ├── OCRSelectionOverlay (ui/ocr_overlay.py) — region capture
  │   └── DownloaderDialog (ui/downloader.py) — model download
  │
  └── Background threads
      ├── FlashWarmup — loads model on startup
      ├── ClipboardMonitor — polls clipboard, emits translations
      ├── LicenseValidate — background license check
      └── OCRCaptureWorker — off-thread OCR processing
```

---

## Database / storage schema

**No traditional database.** Persistence via JSON files in `data/` directory.

**Tables / collections:**
- `data/vault.json` — Translation cache: SHA256 hash → `{translation, original, target_lang, match_type, score}`
- `data/phrases.json` — Gaming slang dictionary: `{lang: {phrase: {en, note}}}`
- `data/meta.json` — Updater state: `{last_check_ts, skipped_version}`
- `data/telemetry.json` — Local telemetry: `{translations: [{src_lang, tgt_lang, text_length, translation_ms, cache_hit, ...}], ...}`
- `config.json` — User settings (language, hotkeys, device, UI preferences)

**Migration history:**
- None yet. Schema is flat JSON, no migrations required.

---

## Project structure

```
babelgg_v2/
├── main.py                  # Entry point + BabelGG coordinator
├── config.json              # Default config (bundled), user config (LocalAppData)
├── version.json             # Model source URLs, quantization configs
├── requirements.txt         # Dependencies
├── BabelGG.spec            # PyInstaller spec (full build)
├── BabelGG_Lite.spec       # PyInstaller spec (Lite build)
├── download_models.py      # First-run model download script
│
├── core/                   # Core business logic
│   ├── flash.py            # Translation engine (large, stable)
│   ├── vault.py            # Translation cache (large, stable)
│   ├── catch.py            # Clipboard monitor
│   ├── slang.py            # Gaming slang normalizer
│   ├── hardware.py         # GPU/RAM detection
│   ├── i18n.py             # UI translations (large, centralized)
│   ├── ocr.py              # EasyOCR wrapper
│   ├── license.py          # Pro license system
│   ├── telemetry.py        # Local telemetry
│   ├── updater.py          # Silent update checker
│   ├── phrase.py           # Phrase lookup helper
│   ├── paths.py            # Path resolution helpers
│   ├── emoji_cleaner.py    # Emoji stripping for translation input
│   └── naturalizer/        # Natural language post-processing
│
├── ui/                     # PyQt6 UI layer
│   ├── card.py             # Floating translation card
│   ├── reply.py            # Reply compose box
│   ├── tray.py             # System tray + hotkeys
│   ├── settings.py         # Settings window (large, complex)
│   ├── downloader.py       # Model download dialog
│   └── ocr_overlay.py      # OCR region selection overlay
│
├── assets/                 # Bundled assets
│   ├── icon.ico            # App icon
│   └── traylogo.png        # Tray icon
│
├── data/                   # Runtime data (created on first run)
│   ├── phrases.json        # Gaming slang (seeded from bundled)
│   ├── vault.json          # Translation cache
│   ├── meta.json           # Updater state
│   └── telemetry.json      # Telemetry
│
├── models/                 # Downloaded models (not in repo)
│   ├── nllb-ct2-cpu/       # CPU quantized model
│   └── nllb-ct2-gpu/       # GPU quantized model
│
├── tests/                  # Test suite
│   ├── run_all.py          # Run all tests
│   ├── test_flash.py       # FlashEngine tests
│   ├── test_vault.py       # TranslationVault tests
│   ├── test_catch.py       # ClipboardMonitor tests
│   ├── test_slang.py       # Slang normalizer tests
│   ├── test_hardware.py    # Hardware detection tests
│   ├── test_emoji_cleaner.py
│   ├── test_naturalizer.py
│   ├── test_license.py
│   ├── test_e2e.py         # End-to-end tests
│   ├── test_flash_router.py
│   ├── test_telemetry.py
│   ├── test_updater.py
│   ├── test_paths.py
│   ├── test_downloader.py
│   └── test_all_languages.py
│
└── _ai/                    # Agent guidance docs
    ├── RULES.md            # Non-negotiable rules
    ├── ARCHITECTURE.md     # This file
    ├── DECISIONS.md        # Why code is the way it is
    ├── BUILD.md            # Build/test instructions
    └── SESSION_HANDOFF.md # Session state transfer
```

---

## External APIs / services in use

| Service | Purpose |
|---------|---------|
| Hugging Face Hub | NLLB-200-distilled-600M model download |
| GitHub raw file | `version.json` for update checking (`raw.githubusercontent.com/aldoud1799/babelGG_v2/main/version.json`) |
| GitHub releases | Update download URL (`github.com/aldoud1799/babelGG_v2/releases`) |
| BabelGG Pro page | License upgrade URL (`babelgg.gg/pro`) |

---

## Common task guidance

**Adding a new language to FlashEngine:**
1. Add entry to `FlashEngine.LANG_CODES` dict (key = display name, value = BCP 47 tag)
2. Add entry to `FlashEngine._CT2_LANG_MAP` for tokenizer mapping
3. If non-Latin script, add to `FlashEngine._NON_LATIN_TARGETS` and `_TARGET_SCRIPT_RANGES`
4. Update `ui/settings.py` language dropdown if needed
5. Run `python tests/run_all.py --extended` to validate

**Fixing a clipboard/translate issue:**
1. Check `data/babelgg.log` for errors
2. Verify `catch.py` is polling (clipboard read working)
3. Check `flash.py` ready state — clipboard monitor starts only after flash ready
4. Run `python tests/run_all.py` to confirm core not broken

**Modifying UI:** All UI runs on main Qt thread. Use `pyqtSignal` to bridge background thread results. Settings changes apply live via hotkey re-registration.