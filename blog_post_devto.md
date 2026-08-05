# I shipped a Python AI app as a Windows installer and the GPU silently stopped working

*Posted on dev.to — copy the body into a new post at dev.to after creating your account.*

---

**Tags**: `python`, `pyinstaller`, `cuda`, `nmt`, `debugging`, `windows`

---

## The setup

I built BabelGG v2 — a small Python app that watches the clipboard and, when you copy foreign text, runs it through an AI translation model (NLLB-200 distilled 600M, served via CTranslate2) and pops up a floating card with the English translation. It's a gaming-overlay kind of thing. Latency target: under a second.

When I ran it from source with `python main.py`, everything worked. The GPU fired up. Translation latency was around 70 ms. I was happy.

Then I packaged it as a Windows installer using PyInstaller (`pyinstaller BabelGG.spec --onedir`) and ran the resulting `BabelGG.exe`. The app started. Translation worked. Cards appeared. But latency was 250 ms instead of 70. The GPU wasn't being used.

There was no error. No log entry. No warning. The app just decided to use the CPU.

This is the story of how I found that bug, and the 80 lines of Python that fix it.

---

## The investigation

I had two deployment artifacts to compare:
- Source-tree execution: GPU at 67 ms median latency
- Frozen executable: CPU at 250 ms median latency

Same model, same hardware, same machine, same code. The only difference was packaging. So the bug had to be in how PyInstaller builds the executable.

PyInstaller freezes your Python script into a standalone binary. When the user runs `MyApp.exe`, it extracts your code into a temp directory, sets up the Python interpreter, and runs your script. One thing PyInstaller does *not* do well: handle native libraries that need to be loaded by `ctypes.CDLL()` or by extension modules that probe the OS for DLLs at import time.

For GPU work, the relevant DLLs are the CUDA runtime:
- `cublas64_12.dll` — NVIDIA cuBLAS
- `cublasLt64_12.dll` — NVIDIA cuBLAS-Lt
- `cudart64_12.dll` — NVIDIA CUDA runtime

When you install CUDA via pip wheels (`nvidia-cublas-cu12`, `nvidia-cuda-runtime-cu12`, `nvidia-cuda-nvrtc-cu12`), these DLLs land in your Python environment. When PyInstaller freezes your app, it bundles them into `_internal/nvidia/cublas/bin/`, `_internal/nvidia/cuda_runtime/bin/`, etc.

But Windows doesn't know to look there. Windows looks for DLLs in:
1. The directory of the executable
2. The system directories
3. The PATH

The bundled `_internal/nvidia/cublas/bin/` is none of those. So when CTranslate2 (or PyTorch, or llama.cpp, or any CUDA library) tries to load `cublas64_12.dll` at process start, Windows can't find it.

When the load fails, the C++ library does the obvious thing: silently disables the GPU backend and falls back to CPU. No exception. No log. From your Python code's perspective, `ctranslate2.Translator(device='cuda')` succeeds — it just returns an object that internally uses CPU.

---

## How I confirmed it

Two checks:

**Check 1: Is `cublas64_12.dll` loadable?**

```python
import ctypes
ctypes.WinDLL('cublas64_12.dll')
# OSError: [WinError 126] The specified module could not be found.
```

**Check 2: Does CTranslate2 see a CUDA device?**

```python
import ctranslate2
print(ctranslate2.get_cuda_device_count())
# 0
```

Both confirmed: CUDA runtime is missing, and CTranslate2 silently reports zero GPUs. The GPU is not used. The CPU does all the work. The user sees translations that take 3-4x longer than expected and blames their hardware.

---

## The fix: two parts

### Part 1: PyInstaller runtime hook (`rthook_dlls.py`, 11 lines)

PyInstaller lets you specify a "runtime hook" — a Python file that runs before any of your code, before any imports. The hook can call `os.add_dll_directory()` to register additional DLL search paths. PyInstaller invokes runtime hooks specified via `runtime_hooks=['rthook_dlls.py']` in the spec file.

```python
# rthook_dlls.py
import os, sys
if hasattr(sys, '_MEIPASS'):
    base = sys._MEIPASS
    for sub in ['', 'nvidia/cublas/bin',
                'nvidia/cuda_nvrtc/bin',
                'nvidia/cuda_runtime/bin',
                'data/cuda/bin']:
        d = os.path.join(base, sub)
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
```

This runs as the very first thing in the frozen executable. By the time CTranslate2 imports, the DLL search path is configured.

### Part 2: Belt-and-suspenders enumeration (`core/hardware.py`)

The runtime hook only fires if PyInstaller invokes it. For dev environments, containerized deployments, or non-PyInstaller distributions, we need an equivalent call site. I added a function that enumerates every plausible CUDA install location and calls `os.add_dll_directory()` on each:

```python
# core/hardware.py
def _add_windows_cuda_dirs() -> list[str]:
    if os.name != 'nt' or not hasattr(os, 'add_dll_directory'):
        return []
    roots = []
    # CUDA_PATH environment variable
    for key, value in os.environ.items():
        if key.startswith('CUDA_PATH') and value:
            roots.append(value)
    # Standard NVIDIA install path
    if os.environ.get('ProgramFiles'):
        toolkit_root = os.path.join(os.environ['ProgramFiles'],
                                     'NVIDIA GPU Computing Toolkit', 'CUDA')
        if os.path.isdir(toolkit_root):
            for entry in sorted(os.listdir(toolkit_root), reverse=True):
                roots.append(os.path.join(toolkit_root, entry))
    # PyInstaller-bundled DLLs
    exe_dir = os.path.dirname(sys.executable)
    roots.extend([
        exe_dir,
        os.path.join(exe_dir, '_internal'),
        os.path.join(exe_dir, '_internal', 'nvidia', 'cublas', 'bin'),
        os.path.join(exe_dir, '_internal', 'nvidia', 'cuda_nvrtc', 'bin'),
        os.path.join(exe_dir, '_internal', 'nvidia', 'cuda_runtime', 'bin'),
        os.path.join(exe_dir, 'data', 'cuda', 'bin'),
    ])
    # pip wheel installs
    for p in sys.path:
        if not p:
            continue
        roots.extend([
            os.path.join(p, 'nvidia', 'cublas', 'bin'),
            os.path.join(p, 'nvidia', 'cuda_nvrtc', 'bin'),
            os.path.join(p, 'nvidia', 'cuda_runtime', 'bin'),
        ])
    # Dedupe and add
    added = []
    seen = set()
    for root in roots:
        if not root:
            continue
        bin_dir = os.path.join(root, 'bin') if not root.lower().endswith('bin') else root
        norm = os.path.normcase(os.path.normpath(bin_dir))
        if norm in seen or not os.path.isdir(bin_dir):
            continue
        seen.add(norm)
        try:
            os.add_dll_directory(bin_dir)
            added.append(bin_dir)
        except Exception:
            continue
    return added
```

Call this **before** any CUDA library import.

### Part 3: Verification

The fix is useless if we don't know it actually worked. So I added a pre-flight check that runs before any GPU compute profile is accepted:

```python
def _ct2_cuda_preflight(self, ctranslate2_module):
    if os.name == 'nt':
        required = ('cublas64_12.dll', 'cublasLt64_12.dll', 'cudart64_12.dll')
        for dll_name in required:
            try:
                ctypes.WinDLL(dll_name)
            except Exception as e:
                return False, f'missing {dll_name}: {e}'
    try:
        count = int(ctranslate2_module.get_cuda_device_count())
    except Exception as e:
        return False, f'cuda probe failed: {type(e).__name__}: {e}'
    if count <= 0:
        return False, 'no CUDA devices reported by ctranslate2'
    return True, f'cuda devices={count}'
```

And a runtime recovery path that catches CUDA errors mid-execution and switches to CPU:

```python
def _recover_ct2_to_cpu(self, reason):
    if self.runtime != 'ctranslate2' or self.device == 'cpu':
        return False
    self.device = 'cpu'
    self._ct2_translator = None
    self._ct2_tokenizer = None
    # ... reset and reload on CPU model
    return self._ensure_profile('cpu_safe')
```

The recovery pattern-matches error messages for `cublas`, `cudnn`, `cuda`, `cudart`, `cublas64_`, `cannot be loaded`, `not found`, `dll` — every phrase the CUDA runtime has historically surfaced when it fails to find a DLL.

---

## The numbers, after the fix

Measured on my dev box — RTX 3080, CUDA 13.3 driver, CTranslate2 4.7.1:

| Mode | Median latency |
|---|---|
| Before fix (silent GPU→CPU fallback) | 250 ms |
| After fix (GPU active) | 67 ms |

That's a 3.7× speedup. Nothing exotic, but it's the difference between "translation feels instant" and "translation feels sluggish" in an interactive overlay.

---

## The deeper lesson

Two patterns bit me here. Both are common in production AI deployment.

**Pattern 1: Silent fallback is the worst kind of failure.** When your code "works but is slow," you have no diagnostic signal. There's no exception to catch, no error log to grep. Your only signal is the latency differential — and latency is noisy enough that a 3-4× slowdown can hide in plain sight for weeks. The fix is to make the silent paths loud: log when fallbacks happen, expose what device each call used, surface this in a status UI.

**Pattern 2: Packaging is the long tail of deployment.** Your model works in dev. Your tests pass. The model loads. The inference runs. Everything looks fine. Then you package it as an installer and 6 months of subtle issues surface because the runtime environment is different from your dev environment. PyInstaller on Windows is the worst offender — it does its own thing with native libraries, with its own conventions, with documentation that lags behind the libraries it bundles.

---

## Try it

The fix is at https://github.com/aldoud1799/babelGG_v2. The full `rthook_dlls.py` is 11 lines. The hardware detection is in `core/hardware.py`. The verification is in `core/flash.py`. The paper documenting the bug, the fix, and the numbers is in the repo.

If you're shipping CUDA-dependent Python code as a Windows PyInstaller executable, you almost certainly have this bug. Check it with:

```python
import ctypes
try:
    ctypes.WinDLL('cublas64_12.dll')
    print("CUDA runtime DLLs are findable")
except OSError as e:
    print(f"Bug present: {e}")
```

If you see "Bug present", copy `rthook_dlls.py` from the repo, add it to your PyInstaller spec's `runtime_hooks`, and ship.

---

*Have you hit this? Found a different fix? Hit me up — this is a class of bug I suspect affects every Python CUDA Windows deployment.*