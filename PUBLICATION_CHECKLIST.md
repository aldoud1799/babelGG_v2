# Publication Checklist — BabelGG v2 Paper v1.0

Everything below is prepared and waiting. You just need to execute.

---

## Part 1: GitHub + Zenodo (immediate)

The commit `1af0fac` is ready locally with tag `v1.0-paper`.

### Step 1.1 — Push to GitHub

```bash
cd D:/AbeSoft/BabelGG_v2
git push origin master
git push origin v1.0-paper
```

You should already have push access to `https://github.com/aldoud1799/babelGG_v2`. If not, fix that first.

### Step 1.2 — Create GitHub release

1. Go to https://github.com/aldoud1799/babelGG_v2/releases/new
2. Choose tag: **v1.0-paper**
3. Title: **BabelGG v2 — Paper v1.0: CUDA Silent-Fallback Fix + Detection Gap + Beam Quality Findings**
4. Description: paste from `RELEASE_NOTES_v1.0.md` (open it in your editor, copy, paste)
5. Attach `paper.pdf` (it should already be visible as a binary attachment because it's committed)
6. Click **Publish release**

### Step 1.3 — Connect Zenodo

1. Go to https://zenodo.org and sign in (or register; Zenodo accepts any email)
2. Click your avatar → **GitHub** → **Connect** → grant access to `aldoud1799`
3. Zenodo will list your repos. Find **babelGG_v2** and toggle **Enable** for it
4. Zenodo will then listen for new GitHub releases on that repo

### Step 1.4 — Trigger Zenodo DOI minting

You have two options:

**Option A (automatic):** Zenodo picks up releases on the connected repo. Now that you've created v1.0-paper in Step 1.2, Zenodo should automatically create a record for it within ~5 minutes. Go to https://zenodo.org/me/uploads to verify.

**Option B (manual):** If the webhook didn't fire, go to https://zenodo.org/deposit/new and upload `paper.pdf` directly. Fill in:
- Title: same as GitHub release title
- Authors: BabelGG Project
- Description: paste from RELEASE_NOTES_v1.0.md
- Keywords: NLLB-200, CTranslate2, PyInstaller, CUDA, language detection
- License: MIT
- Resource type: Preprint (or Software, your choice)

### Step 1.5 — Verify Zenodo record

After Zenodo processes the release, you'll see:
- A DOI like `10.5281/zenodo.NNNNNNN`
- A citable record with the PDF attached

That's your permanent citation handle. Use it in the arXiv submission abstract later.

---

## Part 2: arXiv (parallel, may take days)

### Step 2.1 — Try arXiv submission again

Go to https://arxiv.org/submit and re-register or sign in. The email warning is a soft suggestion — proceed anyway.

For the submission form:

**Title:**
> BabelGG v2: A Frozen-Executable NLLB-200 Deployment on Windows with a CUDA Silent-Fallback Fix and a Source-Language Detection Fix

**Authors:** BabelGG Project (single author is fine)

**Primary category:** `cs.CL` (Computation and Language)

**Cross-list categories (optional):**
- `cs.SE` (Software Engineering) — relevant because Finding 1 is a packaging bug
- `cs.AI` (Artificial Intelligence) — also relevant

**Abstract:** copy from `paper.md` lines 10-39

**Comments:** "Code, benchmark harness, and reproduction instructions: https://github.com/aldoud1799/babelGG_v2. Companion DOI: 10.5281/zenodo.NNNNNNN (fill in after Zenodo mints it)."

**License:** CC BY 4.0 (paper text). The code in the repo is MIT.

**File format:** Upload `paper.pdf` directly. arXiv accepts PDF for the `pdf` upload field. If you also have source files, you can upload a `.tar.gz` containing `paper.tex` or `paper.md`, but for an engineering paper PDF alone is fine.

**Suggested keywords:**
- NLLB-200
- CTranslate2
- PyInstaller
- CUDA
- Windows
- Language identification
- Neural machine translation
- Multilingual NMT

### Step 2.2 — Endorsement request

arXiv will email you saying your submission needs endorsement before publication. You need to find one arXiv author in `cs.CL` or `cs.AI` willing to endorse you.

#### Who can endorse
Anyone with an existing arXiv account who has previously submitted a paper to `cs.CL` (or `cs.AI`/`cs.SE`). They don't need to know you personally.

#### How to find one
Three practical paths:

1. **Email people who cite similar work.** The NLLB-200 paper authors have arXiv accounts. The CTranslate2 maintainers have arXiv accounts. OpenNMT team members do too. Look at the references section of `paper.md` — most of them are arXiv IDs.

2. **Look at the arXiv endorsement system directly.** After submitting, arXiv may let you request endorsement through their UI. If they offer an "automatic endorser" option, take it (slower but works).

3. **Twitter/X or LinkedIn.** A polite message to an arXiv author with your paper title and link often works. Something like:

> Hi, I've submitted a paper to arXiv on a CUDA silent-fallback bug in CTranslate2 + PyInstaller deployments and a source-language detection fix for NLLB-200. I'm looking for an arXiv endorser in cs.CL. Would you be willing to review the submission and endorse if it looks reasonable? Paper: https://github.com/aldoud1799/babelGG_v2 (paper.pdf attached). Thank you.

#### Template endorsement-request email

```
Subject: arXiv endorsement request — BabelGG v2 paper (cs.CL)

Hi [Name],

I recently submitted a paper to arXiv in the cs.CL category:
"BabelGG v2: A Frozen-Executable NLLB-200 Deployment on Windows
with a CUDA Silent-Fallback Fix and a Source-Language Detection Fix"

The paper documents two engineering findings from building BabelGG v2:
(1) a silent GPU-to-CPU fallback bug in PyInstaller + CTranslate2
deployments on Windows, and (2) a source-language detection gap
in the NLLB-200 deployment that the bundled model itself is
capable of handling when given the right source tag. Both have
reproducible fixes (rthook_dlls.py + fasttext-langdetect pre-step).

arXiv requires an endorsement from an existing author in cs.CL
before publishing. Would you be willing to review the submission
and endorse if it looks reasonable?

Paper PDF, code, and reproduction harness:
  https://github.com/aldoud1799/babelGG_v2

Abstract:
  [paste from paper.md]

Thank you for your time.

— [Your name]
```

### Step 2.3 — While waiting for endorsement

Your paper will sit in the arXiv queue. Endorsement requests can take a few days to a few weeks depending on responsiveness.

In the meantime:
- Your GitHub release is already public
- Your Zenodo DOI is already citable
- You can share the GitHub link on social media, blog posts, mailing lists
- Anyone can read and cite your paper immediately via Zenodo

### Step 2.4 — After endorsement

arXiv will email you. Your paper appears at a permanent URL like `https://arxiv.org/abs/2608.NNNNN`. Add that URL to the GitHub README and Zenodo description as a cross-reference.

---

## Summary timeline

| When | What |
|------|------|
| Today | Push to GitHub, create release, connect Zenodo (~15 min) |
| Today | Submit to arXiv (~15 min) |
| Today-end | Zenodo DOI minted (~hours) |
| 1-7 days | arXiv endorser responds |
| 1-7 days | arXiv paper appears |

---

## What's already done

- ✅ Paper drafted, polished, with measured numbers
- ✅ `paper.pdf` rendered (8 pages)
- ✅ All benchmark scripts in repo, reproducible
- ✅ Git commit with tag v1.0-paper
- ✅ CITATION.cff created
- ✅ Release notes drafted
- ✅ Endorsement email template drafted
- ✅ This checklist written

## What you need to do

1. `git push origin master && git push origin v1.0-paper`
2. Create GitHub release from v1.0-paper tag
3. Connect Zenodo to your GitHub account
4. Submit to arXiv (cs.CL)
5. Email 2-3 potential endorsers
6. Wait

Total active work: ~30-45 minutes. Total wall time to public availability: same day (GitHub + Zenodo), 1-7 days (arXiv).