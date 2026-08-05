# Zenodo Manual Upload — Metadata

If the GitHub integration doesn't auto-mint a DOI, upload `paper.pdf`
directly at https://zenodo.org/deposit/new

---

## Upload

`paper.pdf` (already in your repo at `D:/AbeSoft/BabelGG_v2/paper.pdf`)

## Title

```
BabelGG v2: A Frozen-Executable NLLB-200 Deployment on Windows with a CUDA Silent-Fallback Fix and a Source-Language Detection Fix
```

## Authors

```
BabelGG Project
```

(Or use your real name if you prefer — single author.)

## Description

```
Engineering case study of building BabelGG v2, a real-time offline
translation overlay that wraps the NLLB-200 distilled 600M model via
CTranslate2 with int8_float16 quantization on GPU. Documents two
previously-undocumented findings:

(1) Silent GPU-to-CPU fallback when CTranslate2 is initialized inside
a frozen PyInstaller Windows executable — fix is an 11-line runtime
hook plus a startup DLL enumeration.

(2) Source-language detection limits practical coverage of European-
language inputs; the underlying NLLB model is capable on these inputs
when given the right source language tag — fix is a 30-line
fasttext-langdetect pre-detection step that raises detection accuracy
from 51% to 86%.

Measured on NVIDIA RTX 3080 / CTranslate2 4.7.1: GPU median latency
67 ms, CPU fallback 250 ms (3.7× slower, not 10×), model footprint
~1.2 GB VRAM.

Includes paper.pdf and full benchmark harness in the companion
repository. Beam-size quality sweep with CTranslate2 model log-
probability as a quality proxy: beam=4 produces higher-probability
outputs than beam=1 in 25 of 26 disagreement cases (96%) at 8 ms
median latency overhead.
```

## Keywords

```
NLLB-200; CTranslate2; PyInstaller; CUDA; Windows; language detection;
multilingual NMT; consumer hardware; frozen executable; deployment;
engineering case study
```

## License

```
MIT
```

## Resource type

```
Preprint
```

## Related identifiers (optional, fill in after Zenodo DOI mints)

- Is supplement to: https://github.com/aldoud1799/babelGG_v2

## Funding (leave blank)

```
None
```

## Communities (optional)

- `zenodo` (default — leave as is)

---

## After upload

Zenodo will assign a DOI like `10.5281/zenodo.NNNNNNN`. Save this DOI
— it's your permanent citation handle. Add it to:

- The GitHub release description
- The CITATION.cff file in the repo
- The Hugging Face Papers submission
- The arXiv submission comments (when you eventually submit there)

## Verifying the DOI

After upload, your record will be at:
`https://zenodo.org/records/<NNNNNN>`

Test that:
- The PDF is downloadable
- The DOI resolves
- The metadata is correct