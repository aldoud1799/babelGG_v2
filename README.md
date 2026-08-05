# BabelGG v2

Real-time gaming translation. Copy foreign text → floating card appears in 1 second.

## First Time Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download the translation model (~1.1 GB, one-time)
python download_models.py

# 3. Launch
python main.py
```

## Tech Stack

- **Translation**: SMaLL-100 (`alirezamsh/small100`) via CTranslate2 (`models/small100-ct2`)
- **UI**: PyQt6 floating card, system tray, settings
- **Cache**: SHA256 + fuzzy match vault (500 entries, LRU)
- **Slang**: 140+ gaming terms pre-normalized before translation

## How It Works

1. You are in any game / app / browser and see foreign text
2. Select it and press `Ctrl+C`
3. A floating translation card appears near your cursor within 1 second
4. Card fades after 5 seconds — or pin it, or click Reply to send back

## Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+H` | Toggle BabelGG on/off |
| `Ctrl+Shift+R` | Open Reply Box |
| `Ctrl+Shift+,` | Open Settings |

## Build .exe

```bash
pip install pyinstaller
pyinstaller BabelGG.spec --clean
# Output: dist/BabelGG.exe
```

## Release Build (EXE + Installer)

```powershell
# Canonical release command
.\release.ps1
```

What this does:
- Runs tests (`tests/run_all.py`)
- Builds `dist/BabelGG.exe` with PyInstaller
- Builds `installer/BabelGG_Setup.exe` with Inno Setup (`ISCC.exe`)

Optional:

```powershell
# Skip tests when you already validated this commit
.\release.ps1 -SkipTests
```

If `ISCC.exe` is not found:
- Install Inno Setup 6
- Or add `ISCC.exe` to `PATH`

Smoke test checklist:
- `installer/SMOKE_TEST_CHECKLIST.md`

## Project Structure

```
babelgg_v2/
├── main.py              # App entry point
├── config.json          # User settings
├── version.json         # Version + model config
├── requirements.txt     # Dependencies
├── BabelGG.spec         # PyInstaller spec
├── download_models.py   # First-run model setup
├── core/
│   ├── hardware.py      # GPU/RAM detection
│   ├── flash.py         # Llama.cpp translation engine + adaptive router
│   ├── vault.py         # Translation cache
│   ├── slang.py         # Gaming slang normalizer
│   └── catch.py         # Clipboard monitor
├── ui/
│   ├── card.py          # Floating translation card
│   ├── reply.py         # Reply compose box
│   ├── tray.py          # System tray icon
│   └── settings.py      # Settings window
├── assets/
│   └── icon.ico         # App icon
├── tests/
│   ├── test_hardware.py
│   ├── test_flash.py
│   ├── test_vault.py
│   ├── test_slang.py
│   ├── test_catch.py
│   └── run_all.py       # Run all tests
└── models/              # Created by download_models.py
    └── qwen2.5-1.5b-instruct-q4_k_m.gguf
```

## Run Tests

```bash
python tests/run_all.py
# Expected: 10/10 PASS (core suite)

# Optional extended language matrix
python tests/run_all.py --extended
```
