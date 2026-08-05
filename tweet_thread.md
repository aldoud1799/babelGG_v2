# Tweet / X Thread

Post these in order. One tweet per line. Image suggestions are in brackets.

---

**Tweet 1 (the hook):**

```
Spent two weeks debugging why my Python AI app was 3-4x slower as a
Windows installer than running from source.

No error. No log. The GPU was silently not being used.

Here's what was happening, and the 80 lines that fixed it 🧵
```

**Tweet 2 (the setup):**

```
Setup: Python app wrapping NLLB-200 via CTranslate2 + int8_float16 on
RTX 3080. Packaged with PyInstaller onedir.

Source-tree run: 67 ms median latency.
Frozen .exe run: 250 ms median latency.

Same model. Same hardware. Same code.
```

**Tweet 3 (the discovery):**

```
PyInstaller bundles CUDA runtime DLLs into:
  _internal/nvidia/cublas/bin/cublas64_12.dll
  _internal/nvidia/cuda_runtime/bin/cudart64_12.dll
  _internal/nvidia/cuda_nvrtc/bin/...

Windows doesn't search there. CTranslate2 imports, can't find
cublas64_12.dll, silently disables GPU. No exception. No log.
```

**Tweet 4 (the verification):**

```
ctypes.WinDLL('cublas64_12.dll')
# OSError: [WinError 126] The specified module could not be found.

ctranslate2.get_cuda_device_count()
# 0

Yep. Silent GPU→CPU fallback. Production-grade invisibility.
```

**Tweet 5 (the fix):**

```
The fix: a 11-line PyInstaller runtime hook that runs before any
imports and registers _internal/nvidia/*/bin/ as DLL search paths
via os.add_dll_directory(). Plus a startup enumeration that covers
every plausible CUDA install location.

80 lines total.
```

**Tweet 6 (the second bug):**

```
While debugging I found a second bug: the source-language detector
misidentifies 80% of Spanish/German sentences as English. The
translation engine never gets called — it returns None silently.

Direct CTranslate2 calls on the rejected inputs produce perfect
translations. The model is capable; the front gate is the bottleneck.
```

**Tweet 7 (the second fix):**

```
30-line fix: fasttext-langdetect as a pre-detection step. Detection
accuracy goes from 51% → 86%. German→English failure rate goes from
85% → 0%.

Both bugs are reproducible, both fixes are small. Repo has:
- The bug demonstration
- The fix code
- The benchmark harness
- The paper
```

**Tweet 8 (the link):**

```
Full writeup + reproduction harness:
https://github.com/aldoud1799/babelGG_v2

If you ship CUDA Python as a Windows installer, you almost
certainly have the first bug. Worth checking.
```

---

## Posting tips

- Best time to post: Tuesday-Thursday, 9-11am US Eastern
- Reply to comments — the first hour matters for engagement
- Pin the thread to your profile for 24 hours
- Quote-tweet the thread with a one-line summary on day 2 to catch people who missed it

## Image suggestions

For Tweet 1 (the hook): A screenshot of nvidia-smi showing the
process using GPU memory, or a graph of the latency before/after.

For Tweet 5 (the fix): The diff of `rthook_dlls.py` (only 11 lines
so it fits in one screenshot).

For Tweet 6 (the second bug): A screenshot of `detect_lang()`
returning `eng_Latn` for an obviously Spanish sentence.

Use https://carbon.now.sh/ for code screenshots.