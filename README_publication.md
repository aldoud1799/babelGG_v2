# BabelGG v2 Paper — README

This is the public face of the paper. After creating your GitHub repo, set the repo's **description** to the one-liner below and copy the body to the repo's main `README.md` (replacing or alongside the existing README).

---

## GitHub repo description (one-liner, ~120 chars)

```
PyInstaller + CTranslate2 CUDA silent-fallback fix + NLLB-200 source-language detection fix. Measured on RTX 3080.
```

## GitHub repo topics (set via GitHub UI → About → Topics)

```
python pyinstaller cuda ctranslate2 nllb-200 windows translation pytorch onnx
```

## README.md body

Replace the existing README with this, or append it below the existing project README. Either works.

```markdown
# BabelGG v2 — Paper release

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-coming%20soon-b31b1b.svg)]()
[![Zenodo](https://img.shields.io/badge/zenodo-10.5281%2Fzenodo.NNNNNNN-blue)]()

## The paper

**BabelGG v2: A Frozen-Executable NLLB-200 Deployment on Windows with a CUDA Silent-Fallback Fix and a Source-Language Detection Fix.**

This repository ships:

- [`paper.pdf`](paper.pdf) — the paper, 8 pages
- [`paper.md`](paper.md) — the markdown source
- [`bench/`](bench/) — the full reproducible benchmark harness
- [`core/flash.py`](core/flash.py) — the translation engine with the documented design decisions
- [`rthook_dlls.py`](rthook_dlls.py) — the PyInstaller runtime hook (Finding 1 fix)
- [`core/hardware.py`](core/hardware.py) — the DLL enumeration function (Finding 1 fix)
- Benchmarks, results, and diagnostics in the repository root

## TL;DR

Two engineering findings from building BabelGG v2:

1. **Silent GPU-to-CPU fallback in PyInstaller deployments.** When the bundled NVIDIA runtime DLLs are not on the Windows DLL search path, CTranslate2 falls back to CPU silently — no exception, no log. The fix is a runtime hook + DLL enumeration totaling 80 lines of Python.

2. **Source-language detection limits practical coverage.** The detector misidentifies a substantial fraction of European-language inputs as English. The model is capable; the detector never reaches it. The fix is a 30-line fasttext-langdetect pre-detection step that raises detection accuracy from 51% to 86%.

Measured on NVIDIA RTX 3080, CUDA 13.3, CTranslate2 4.7.1:

- int8_float16 NLLB-200 distilled 600M loads in ~11s, uses ~1.2 GB VRAM
- GPU median latency: **67 ms** when detection succeeds
- CPU fallback median: **250 ms** (3.7× slower, not 10×)
- Beam=4 produces higher-probability outputs than beam=1 in 96% of disagreement cases (25/26) at 8 ms median overhead

## Reproducing

```bash
.venv/Scripts/python.exe bench.py             # §5.2 GPU + CPU latency
.venv/Scripts/python.exe bench_with_fix.py    # §5.8 with-fix translation rates
.venv/Scripts/python.exe bench_detection.py    # §5.8 detection accuracy
.venv/Scripts/python.exe bench_beam_quality.py # §5.5 beam quality sweep
```

## Reading

If you maintain a Python AI app and ship it as a Windows PyInstaller
executable, Finding 1 likely affects you. The fix is small; the
diagnosis takes longer than the fix.

If you maintain any product with a "front gate" ML model that decides
whether to call an expensive downstream model, Finding 2 generalizes.
The pattern of a silent detector failing and an expensive model never
being called is broader than language detection.

## License

MIT for code. CC-BY-4.0 for paper text. See [LICENSE](LICENSE).
```

---

## Personal website / portfolio version (if you have one)

If you want to put this on a personal site as well, the canonical citation block is:

```markdown
**Citation**

Abdullah Abbas Eldoud Hamad. (2026). *BabelGG v2: A Frozen-Executable
NLLB-200 Deployment on Windows with a CUDA Silent-Fallback Fix and a
Source-Language Detection Fix.* BabelGG Project.
https://github.com/aldoud1799/babelGG_v2
```

Or in BibTeX form (for anyone citing in academic work):

```bibtex
@misc{babelgg2026cuda,
  author = {Abdullah Abbas Eldoud Hamad},
  title  = {BabelGG v2: A Frozen-Executable {NLLB-200} Deployment on
            Windows with a {CUDA} Silent-Fallback Fix and a
            Source-Language Detection Fix},
  year   = {2026},
  month  = aug,
  url    = {https://github.com/aldoud1799/babelGG_v2},
  note   = {BabelGG Project}
}
```