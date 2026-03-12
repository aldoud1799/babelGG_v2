# BabelGG v2

Real-time gaming translation. Copy foreign text → floating card appears in 1 second.

## First Time Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download and convert the translation model (~1.5 GB, one-time)
python download_models.py

# 3. Launch
python main.py
```

## Tech Stack

- **Translation**: NLLB-200 distilled 600M via CTranslate2 (CUDA int8)
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
│   ├── flash.py         # NLLB translation engine
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
    ├── nllb-200-distilled-600M/
    └── nllb-ct2/
```

## Run Tests

```bash
python tests/run_all.py
# Expected: 5/5 PASS
```
