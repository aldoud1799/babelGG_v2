# BUILD.md — BabelGG v2

Build commands, test instructions, and environment setup. Load this only when the task involves building, installing, or running tests.

---

## Environment

- **Machine:** Windows 11 Pro 10.0.26200
- **Python:** 3.x (native, not conda)
- **Build tool:** PyInstaller 6.x
- **Installer tool:** Inno Setup 6 (for `release.ps1`)

---

## Build

```bash
# Development build (from source)
pip install -r requirements.txt
python main.py

# Frozen exe build
pyinstaller BabelGG.spec --clean
# Output: dist/BabelGG/BabelGG.exe

# Lite build (if BabelGG_Lite.spec exists)
pyinstaller BabelGG_Lite.spec --clean

# Unpacked spec (for debugging)
pyinstaller BabelGG_unpacked.spec --clean
```

---

## Install and run

```bash
# First-time setup
pip install -r requirements.txt
python download_models.py
python main.py
```

---

## Logs

```bash
# Real-time log tail (Windows)
Get-Content data\babelgg.log -Wait -Tail 50

# Or in-app: Settings → Logs (if implemented)
```

---

## Tests

```bash
# Core test suite
python tests/run_all.py

# Extended language matrix
python tests/run_all.py --extended

# Single test
python -m pytest tests/test_flash.py -v
# or
python tests/test_flash.py
```

**Test output expected:** 10/10 PASS (core suite)

---

## Known acceptable failures

> None currently confirmed. If a test fails on specific hardware (e.g., no GPU), document it here.

- **[Test ID]:** [Reason] — None yet identified.

---

## Quality gates — do not mark a task done until all pass

| Gate | Requirement |
|------|-------------|
| Build | `pyinstaller BabelGG.spec --clean` succeeds without error |
| Core tests | `python tests/run_all.py` — 10/10 PASS |
| Extended tests | `python tests/run_all.py --extended` — acceptable failures documented |
| Runtime | No crashes on startup, no import errors |
| Translation latency | < 2s for typical gaming text on CPU |

---

## Build configuration notes

- **PyInstaller runtime hook (`rthook_dlls.py`):** Adds CUDA/NVIDIA DLL directories to `os.add_dll_directory()` at startup for frozen exe. This fixes `cublas.dll` not found errors on GPU builds.
- **Hidden imports:** llama_cpp, ctranslate2, transformers, sentencepiece, pyperclip, keyboard, PyQt6, GPUtil, psutil, thefuzz — all needed at runtime but not auto-detected by PyInstaller.
- **Excludes:** torch, torchvision, torchaudio, matplotlib, notebook, tensorboard — these are not used and add enormous bloat.
- **Data files in spec:** phrases.json, version.json, model files — these must be in datas or they won't be found at runtime.
- **RTF hook (`rthook_dlls.py`)** uses `sys._MEIPASS` to find CUDA DLLs in frozen exe `_internal` folder.

---

## Release build

```powershell
# Canonical release (exe + Inno Setup installer)
.\release.ps1

# Skip tests (when already validated)
.\release.ps1 -SkipTests
```

Requires: PyInstaller, Inno Setup 6 (ISCC.exe in PATH).

Output: `dist/BabelGG.exe` (portable) + `installer/BabelGG_Setup.exe` (installer)