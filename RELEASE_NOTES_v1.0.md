# BabelGG v2 — Paper Release v1.0

This release accompanies the paper **"BabelGG v2: A Frozen-Executable NLLB-200 Deployment on Windows with a CUDA Silent-Fallback Fix and a Source-Language Detection Fix"**.

## What this paper contributes

Two previously undocumented engineering findings from building a real-time
NLLB-200 deployment on consumer Windows hardware:

1. **Silent GPU-to-CPU fallback in PyInstaller deployments.** CTranslate2
   packaged as a frozen Windows executable silently falls back to CPU when
   the bundled CUDA runtime DLLs are not on the Windows DLL search path.
   No exception, no log entry, no error surfaced. The fix is a PyInstaller
   runtime hook (`rthook_dlls.py`, 11 lines) plus an explicit
   `os.add_dll_directory` enumeration (`core/hardware.py:17-68`).

2. **Source-language detection limits practical coverage.** The engine's
   charset-based + marker-word + `langdetect` pipeline misidentifies a
   substantial fraction of European-language inputs as English. Direct
   CT2 calls produce valid translations on every rejected input, so the
   underlying model is capable — the front gate is the bottleneck.
   A 30-line `fasttext-langdetect` pre-detection fix raises detection
   accuracy from 51% to 86% and drops the German → English failure rate
   from 85% to 0%.

## Measured on this hardware (NVIDIA RTX 3080, 10 GB, CUDA 13.3, CTranslate2 4.7.1)

- int8_float16 NLLB-200 distilled 600M loads in ~11 s cold, occupies ~1.2 GB VRAM
- GPU median translation latency: **67 ms** when detection succeeds
- CPU fallback median: **250 ms** (3.7× slower, not 10×)
- Beam=4 produces higher-probability outputs than beam=1 in 25 of 26
  disagreement cases (96%) on a 70-sentence corpus, at 8 ms median
  latency cost

## Files in this release

| File | What it is |
|------|------------|
| `paper.pdf` | Rendered PDF of the paper (8 pages) |
| `paper.md` | Markdown source of the paper |
| `paper.html` | HTML intermediate used for PDF rendering |
| `build_pdf.py` | Reproduces the PDF from `paper.md` |
| `paper_template.html` | HTML/CSS template used by `build_pdf.py` |
| `CITATION.cff` | Citation metadata for GitHub/Zenodo |
| `bench.py` | Reproduces §5.2 and §5.4 latency benchmarks |
| `bench_with_fix.py` | Reproduces §5.8 with-fix translation failure rates |
| `bench_detection.py` | Reproduces §5.8 detection-accuracy comparison |
| `bench_beam_quality.py` | Reproduces §5.5 beam-size quality sweep |
| `bench_results.json` / `bench_results_with_fix.json` / `bench_beam_quality_results.json` | Raw benchmark output |
| `diag_detection.py` / `diag_residual_failures.py` | Detection diagnostics |
| `diagnose_failures.py` / `trace_*.py` | Engineering investigation scripts used to find the §5.7 root cause |
| `rthook_dlls.py` | The PyInstaller runtime hook (Finding 1 fix) |
| `core/hardware.py` | The DLL enumeration function (Finding 1 fix) |
| `core/flash.py` | The translation engine (contains §4 / §5 documented design decisions) |

## Reproducing the benchmarks

```bash
# In the project venv, with CUDA toolkit 13.x and an NLLB-capable GPU:
.venv/Scripts/python.exe bench.py             # ~10 min, GPU + CPU latency
.venv/Scripts/python.exe bench_with_fix.py    # ~5 min, with fasttext fix
.venv/Scripts/python.exe bench_detection.py    # ~1 min, detection accuracy
.venv/Scripts/python.exe bench_beam_quality.py # ~10 min, beam sweep
```

All four scripts are idempotent, write raw output to `bench_results*.json`,
and assume the NLLB model directories already exist under
`models/nllb-ct2-cpu/` and `models/nllb-ct2-gpu/`.

## License

MIT. The paper text is licensed CC-BY-4.0; the code is MIT.