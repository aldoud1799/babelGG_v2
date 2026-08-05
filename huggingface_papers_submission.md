# Hugging Face Papers — Submission Content

Copy-paste these fields into https://huggingface.co/papers/submit

---

## Title

```
BabelGG v2: A Frozen-Executable NLLB-200 Deployment on Windows with a CUDA Silent-Fallback Fix and a Source-Language Detection Fix
```

## Authors

```
Abdullah Abbas Eldoud Hamad (BabelGG Project)
```

(If you prefer "BabelGG Project" alone, use that. Single-author submissions are fine.)

## Abstract

```
We report two engineering findings from building BabelGG v2, a
frozen-Windows-executable deployment of NLLB-200 distilled 600M via
CTranslate2 with int8_float16 quantization on GPU. Both findings are
previously undocumented and operationally significant.

Finding 1: Silent GPU-to-CPU fallback in PyInstaller deployments. When
CTranslate2 is initialized inside a frozen PyInstaller Windows
executable, and the bundled NVIDIA runtime DLLs (cublas64_12.dll,
cublasLt64_12.dll, cudart64_12.dll) are not discoverable through the
Windows DLL search path at process start, the CTranslate2 translator
falls back to CPU silently — no exception, no log entry on the
user-facing side, no error surfaced through
ctranslate2.get_cuda_device_count(). The fallback is invisible at the
API level and produces correct translations at substantially degraded
latency. We isolate the root cause to the PyInstaller frozen-executable
DLL search path and present a two-component fix: a PyInstaller runtime
hook (rthook_dlls.py, 11 lines) plus an explicit os.add_dll_directory
enumeration (core/hardware.py:17-68) called before any CTranslate2
import. A two-stage verification system — preflight (core/flash.py:511-526)
plus runtime CUDA-error recovery (core/flash.py:617-644) — catches the
failure mode at both startup and runtime.

Finding 2: Source-language detection limits practical coverage. The
engine's source-language detector, based on Unicode charset analysis
plus a small marker-word heuristic and the langdetect library,
misidentifies a substantial fraction of European-language inputs as
English. Spanish and German sentences that lack the heuristic marker
words are flagged as English roughly 80% of the time; the engine then
short-circuits with src == tgt and returns None without invoking the
translation model. Direct calls to CTranslate2 on the same rejected
inputs produce valid translations in every case we tested, so the
model is capable and the detection pipeline is the bottleneck. We
integrate fasttext-langdetect as a 30-line pre-detection step that
raises detection accuracy from 51% to 86% on the benchmark corpus
and drops the German → English failure rate from 85% to 0%.

Measured characteristics on a workstation with an NVIDIA RTX 3080
(10 GB) and CTranslate2 4.7.1: the int8_float16 NLLB-200 distilled
600M model loads in ~11 s cold and runs at a median latency of
approximately 67 ms per translation across a 10-language-pair matrix
when the call succeeds. The CPU fallback path (int8 quantization on
the same model) achieves a median latency of approximately 250 ms —
roughly 3.7× slower than GPU on the same task, far less than the
10× penalty commonly assumed.
```

## Tags / Keywords

```
nllb-200, ctranslate2, pyinstaller, cuda, windows, language-detection,
multilingual-nmt, consumer-hardware, deployment, engineering,
preprint
```

## Primary URL (link to your paper)

If Zenodo DOI is minted: `https://doi.org/10.5281/zenodo.NNNNNNN`

If not yet: `https://github.com/aldoud1799/babelGG_v2/releases/tag/v1.0-paper`

(Pick whichever is live first.)

## Code / Repository URL

```
https://github.com/aldoud1799/babelGG_v2
```

## Type

Preprint

## License

CC BY 4.0

---

## What to expect after submitting

Hugging Face Papers submissions are reviewed by the HF team. Typical
turnaround: 1-5 days. Your paper will appear at
`https://huggingface.co/papers/<id>` and be visible to anyone who
browses ML papers on HF. The HF papers page is indexed by Google
Scholar, so your work will be findable via academic search.

HF may also auto-merge your paper into the arXiv feed if you provide
an arXiv ID later — useful to do after endorsement finally lands.