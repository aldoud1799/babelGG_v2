# BabelGG v2 Progress Report
Date: 2026-04-07
Status: Active implementation checkpoint

## 1. Scope Completed In This Session

### 1.1 Packaging and Installer Reliability
- Removed bundled GGUF from app payload in `BabelGG.spec`.
- Added release guard in `release.ps1` to fail build if GGUF is accidentally bundled again.
- Fixed release output path mismatch (`onedir`):
  - `release.ps1` now validates `dist/BabelGG/BabelGG.exe`.
- Fixed installer payload definition:
  - `installer/BabelGG.iss` now packages the full `dist/BabelGG/*` tree recursively.
- Rebuilt installer successfully multiple times.
- Verified fresh installer installs successfully via silent install logs.

### 1.2 First-Run Downloader Hardening
- Added retry logic and friendlier error mapping in `ui/downloader.py`.
- Added optional SHA256 model verification support.
- Reworked downloader for better throughput:
  - larger chunk size,
  - throttled UI updates,
  - token-aware requests,
  - parallel ranged download mode for large files,
  - live MB/s status display.
- Added support for HF token (config/env) to improve authenticated throughput.

### 1.3 Installer UX Improvements
- Improved `installer/BabelGG.iss` with modern setup metadata and behavior:
  - 64-bit install mode,
  - cleaner wizard flow,
  - optional desktop shortcut task,
  - branded setup icon.
- Added custom installer artwork assets:
  - `assets/installer_wizard.bmp`
  - `assets/installer_wizard_small.bmp`

### 1.4 Runtime Path and Permission Fixes
- Migrated frozen-runtime write paths to user-writable LocalAppData:
  - data and models in `core/paths.py`.
- Updated runtime config save path for frozen builds in `main.py`:
  - config now saved under LocalAppData, not Program Files.
- Added runtime data seeding in `main.py`:
  - copies packaged defaults (`phrases.json`, `meta.json`, `telemetry.json`, `vault.json`) into user data dir when missing.
- Hardened single-instance lock acquisition path and logging in `main.py`.

### 1.5 Translation and Reply Behavior Fixes
- In `core/flash.py`:
  - sticky routing now permits lower profiles before deterministic fallback,
  - timeout now tries next profile instead of immediate fallback text.
- In `core/catch.py`:
  - unchanged fallback output (translation == source) is suppressed from card emission.
- In `ui/reply.py`:
  - unchanged fallback output is not accepted as reply translation,
  - user sees timeout guidance in preview instead.

### 1.6 Test and Validation Updates
- Added downloader regression test file:
  - `tests/test_downloader.py`.
- Included it in test runner:
  - `tests/run_all.py`.
- Updated sticky-profile expectation test:
  - `tests/test_flash_router.py`.
- Re-ran tests after major changes.

## 2. Validation Results (This Session)

### 2.1 Test Suite
- Core suite passed after final patches: 11/11.
- Extended suite passed at earlier checkpoints when run in release flow.

### 2.2 Installer Build + Install
- Fresh `installer/BabelGG_Setup.exe` built successfully after each major packaging change.
- Silent install logs repeatedly confirmed successful installation.

### 2.3 Runtime and First-Run Download
- LocalAppData runtime log path active:
  - `C:/Users/PC/AppData/Local/BabelGG/data/babelgg.log`.
- First-run model download completed successfully in latest verified run.
- Model present at:
  - `C:/Users/PC/AppData/Local/BabelGG/models/qwen2.5-1.5b-instruct-q4_k_m.gguf`.
- App reached ready state after download/warmup:
  - Flash warmup complete,
  - clipboard monitor started,
  - tray status ready.

## 3. Key Root Causes Identified and Resolved

1. Old installer artifact confusion and path mismatch
- Cause: release script expected one-file exe while build produced one-dir output.
- Fix: aligned release + installer scripts to actual `onedir` output.

2. Installer looked machine-specific
- Cause: stale artifact and packaging inconsistency.
- Fix: deleted old setup, rebuilt from source, validated install from fresh artifact.

3. Downloader stuck/perceived freeze at low progress
- Cause: blocking behavior and sparse meaningful progress updates.
- Fix: resumable streaming + throughput status + retries + higher throughput tuning.

4. Permission errors writing under Program Files
- Cause: runtime attempting to write models/config into install directory.
- Fix: moved frozen runtime writes to LocalAppData paths.

5. Translation/reply showing source text
- Cause: deterministic fallback output surfaced as if successful translation.
- Fix: profile retry before fallback + unchanged-output suppression in card and reply paths.

## 4. Files Changed In This Session

- `PLAN_2026-04-06.md`
- `BabelGG.spec`
- `release.ps1`
- `installer/BabelGG.iss`
- `assets/installer_wizard.bmp`
- `assets/installer_wizard_small.bmp`
- `ui/downloader.py`
- `core/paths.py`
- `main.py`
- `core/flash.py`
- `core/catch.py`
- `ui/reply.py`
- `requirements.txt`
- `tests/run_all.py`
- `tests/test_downloader.py`
- `tests/test_flash_router.py`

## 5. Current State Snapshot

- Installer is rebuildable and installable from current workspace.
- First-run model setup uses user-writable paths and can complete.
- Download path is significantly hardened and enhanced.
- Card/reply logic now guards against unchanged fallback output.
- Core tests pass.

## 6. Recommended Next Step (Next Session)

1. Run one final manual QA pass on the newest installer:
- clean install,
- first-run download,
- translation card output quality,
- reply output quality,
- settings persistence and restart behavior.

2. Capture a short acceptance checklist result in this report and mark public-stable readiness decision.

## 7. Continuation Plan (2026-04-08)

### 7.1 Execution Order
1. Rebuild installer from current workspace state.
2. Perform clean install on a test machine/profile.
3. Validate first-run download completion and ready-state logs.
4. Validate translation card and reply quality with mixed inputs.
5. Validate settings persistence across restart.
6. Run full automated test suite and attach pass/fail summary.

### 7.2 Acceptance Checklist (Fill During Run)
- [ ] Build succeeds and produces `installer/BabelGG_Setup.exe`.
- [ ] Silent/interactive install completes without errors.
- [ ] First-run model download reaches 100% and file hash (if enabled) verifies.
- [ ] Tray reports ready; warmup and monitor startup logs are present.
- [ ] Card output avoids unchanged-source fallback text.
- [ ] Reply output avoids unchanged-source fallback text.
- [ ] Settings changes persist after app restart.
- [ ] Test suite passes with no regressions.

### 7.3 Evidence To Capture
- Installer build timestamp and artifact size.
- Install log location and final success line.
- Runtime log excerpt from LocalAppData showing:
  - model download completion,
  - flash warmup complete,
  - tray ready.
- Test run summary (`tests/run_all.py`) with final pass count.

### 7.4 Readiness Decision Gate
- Mark **Public Stable: YES** only if all checklist items pass.
- If any item fails, mark **Public Stable: NO** and log blocker(s) with owner + fix ETA.

## 8. Continuation Execution Log (2026-04-08)

### 8.1 Automated Regression Status
- Ran `tests/run_all.py` via workspace task (`Run BabelGG tests`).
- Result: **11/11 tests passed**.
- Observed passing modules in output included:
  - `test_hardware.py`
  - `test_flash.py`
  - `test_flash_router.py`
  - `test_downloader.py`
  - `test_vault.py`
  - `test_slang.py`
  - `test_emoji_cleaner.py`
  - `test_naturalizer.py`
  - `test_catch.py`

### 8.2 Remaining Manual QA Items
- Clean installer build + install verification.
- First-run download UX and runtime-ready confirmation.
- Translation/reply quality spot checks.
- Settings persistence across restart.

### 8.3 Installer Build + Clean Install (2026-04-08)
- Ran canonical release flow: `./release.ps1`.
- Release completed successfully.
- Packaging sanity check: no `*.gguf` found in `dist/BabelGG` or `C:/Program Files/BabelGG`.
- Produced artifacts:
  - `installer/BabelGG_Setup.exe` (52.47 MB, 2026-04-08 15:44:29)
  - `dist/BabelGG/BabelGG.exe` (12.15 MB, 2026-04-08 15:43:45)
- Performed clean reinstall sequence:
  - Silent uninstall via `C:/Program Files/BabelGG/unins000.exe` (exit 0)
  - Silent install via `installer/BabelGG_Setup.exe` (exit 0)
- Install evidence logs:
  - `installer/uninstall_silent_2026-04-08.log`
  - `installer/install_silent_2026-04-08.log`
- Installer log confirms: `Installation process succeeded.`
- Interactive installer watch run also completed:
  - Log: `installer/install_interactive_2026-04-08.log`
  - Confirmed sequence: `Installation process succeeded` -> app `Run entry` (`C:/Program Files/BabelGG/BabelGG.exe`) -> `Deinitializing Setup` -> `Log closed`.

### 8.4 Runtime Evidence Snapshot (LocalAppData)
- Runtime log exists at:
  - `C:/Users/PC/AppData/Local/BabelGG/data/babelgg.log`
- Verified key readiness markers in log history:
  - `[DOWNLOADER] GGUF model ready.`
  - `[FLASH] Warmup complete`
  - `[CATCH] Clipboard monitor started`
  - `[TRAY] Status: Ready`
- Model exists at:
  - `C:/Users/PC/AppData/Local/BabelGG/models/qwen2.5-1.5b-instruct-q4_k_m.gguf`
  - Size: 1065.56 MB

### 8.5 Checklist Status (As Of 2026-04-08)
- [x] Build succeeds and produces `installer/BabelGG_Setup.exe`.
- [x] Silent install completes without errors.
- [x] Tray-ready/warmup/monitor startup markers present in runtime log (historical verified run).
- [ ] First-run download UX re-validated from a truly fresh user state in this pass.
- [ ] Card output quality spot-check completed in interactive UI session.
- [ ] Reply output quality spot-check completed in interactive UI session.
- [ ] Settings persistence across restart manually verified in interactive UI session.

## 9. Incident Analysis: Tray Active But No Translation / Reply Output (2026-04-08)

### 9.1 Symptom
- App is visible in tray and reports Ready.
- Clipboard capture events are logged.
- Card/reply output is often empty or appears as "no translation" to user.

### 9.2 Evidence Collected
1. Runtime logs show healthy startup path:
- `[FLASH] Warmup complete`
- `[CATCH] Clipboard monitor started`
- `[TRAY] Status: Ready`

2. Runtime logs show translation attempts failing under routing budget:
- `Profile gpu_trim timed out; trying next profile`
- `Suppressing unchanged fallback translation`

3. Reproduction via direct engine call confirms deterministic fallback under current budget:
- Input: short Korean text (`진짜 웃겨요 ㅋㅋ`)
- Result at current defaults: timeout warning + fallback output (source text unchanged)
- Total call time observed: ~411 ms with profile fallback result

4. Re-test with relaxed budget confirms translations succeed:
- Raised budget test yielded translated output (`Really funny, ㅋㅋ`) with ~504 ms execution

### 9.3 Root Cause
Primary cause:
- Translation latency budget is too aggressive for current runtime/profile defaults.
- `core/flash.py` enforces a hard request budget of 400 ms (`_ABS_BUDGET_MS = 400`), which is below observed normal inference time for short real-world inputs on this system (~500 ms).

Contributing implementation behavior:
- On timeout, the engine tries next profile, but generation runs inside a worker that holds a shared lock.
- If the timed-out worker is still running, subsequent profile attempts may fail lock acquisition quickly and fall through to deterministic fallback.
- Downstream guards correctly suppress unchanged fallback text in `core/catch.py` and `ui/reply.py`, which appears to user as "nothing happened".

Secondary observation:
- Some captured clipboard samples are mojibake/garbled (encoding-distorted text), which can further reduce successful translation quality, but this is not the primary blocker for total no-output behavior.

### 9.4 Why Reply Translation Also Fails
- Reply preview uses the same `FlashEngine.translate()` path.
- When fallback returns unchanged text, `ui/reply.py` intentionally rejects it and shows timeout guidance.
- Therefore card and reply fail together under the same timeout pressure.

### 9.5 Remediation Plan
Phase 1 (Immediate hotfix, low risk):
1. Raise latency budgets in `core/flash.py` to realistic values for desktop inference.
2. Add explicit logging when a profile is skipped due to lock contention (currently mostly silent).
3. Rebuild and run smoke translation/reply checks with Korean/Japanese short inputs.

Proposed starting values:
- `_SOFT_BUDGET_MS`: 280 -> 700
- `_HARD_BUDGET_MS`: 380 -> 900
- `_ABS_BUDGET_MS`: 400 -> 1200

Phase 2 (Stability fix, medium risk):
1. Refactor timeout worker/locking so timed-out generation cannot starve follow-up profile attempts.
2. Separate model-switch lock from generation lock, or avoid profile fall-through while prior worker is still active.
3. Add backpressure to prevent repeated timed-out worker buildup during rapid clipboard events.

Phase 3 (Quality and observability):
1. Add explicit telemetry/log counters for:
- timeout count by profile,
- lock contention skips,
- fallback-suppressed events.
2. Add regression tests for:
- timeout path not producing silent no-output loops,
- reply preview behavior under timeout,
- profile failover producing at least one user-visible diagnostic signal.

### 9.6 Verification Plan After Fix
1. Functional checks:
- Copy Korean and Japanese lines -> translation card appears with translated English output.
- Open reply (Ctrl+Shift+R) -> preview resolves to target language and copy/send works.

2. Log checks:
- No repeated timeout->silent-suppress loop for short inputs.
- If fallback occurs, reason is visible and actionable in logs.

3. Release gate update:
- Keep Public Stable decision as NO until translation and reply checks pass on fresh installer run.

## 10. Hotfix Applied + Installed Runtime Validation (2026-04-08)

### 10.1 Code Fix Implemented
- Updated `core/flash.py` runtime latency budgets:
  - `_SOFT_BUDGET_MS`: 700
  - `_HARD_BUDGET_MS`: 900
  - `_ABS_BUDGET_MS`: 1200
- Improved profile-lock handling in `translate()`:
  - two-attempt lock acquisition with short retry,
  - explicit lock-contention warning before skipping profile.

### 10.2 Test Status After Fix
- Updated `tests/test_flash_router.py` slow-streak timings to align with new hard budget threshold.
- Re-ran full suite: **11/11 tests passed**.

### 10.3 Rebuild + Reinstall
- Rebuilt release via `./release.ps1` successfully.
- Reinstalled patched setup silently:
  - `installer/install_patched_2026-04-08.log`
  - Installer confirms `Installation process succeeded.`

### 10.4 Installed-App Smoke Test (Live)
- Launched installed binary: `C:/Program Files/BabelGG/BabelGG.exe`.
- Confirmed ready state in runtime log:
  - `[FLASH] Warmup complete`
  - `[CATCH] Clipboard monitor started`
  - `[TRAY] Status: Ready`
- Injected Korean clipboard text and observed translated card output in installed app log:
  - Detected: `진짜 웃겨요 ㅋㅋ`
  - Card: `Really funny, ㅋㅋ`
- Additional live samples also produced translated card outputs (Japanese/Korean examples) without timeout-suppress loop.

### 10.5 Reply Path Validation Status
- Reply translation path uses the same `FlashEngine.translate()` backend as card translation.
- Installed build confirms backend recovery under live clipboard workload.
- Automated terminal-only triggering of reply UI send-flow was inconclusive in this run (global key injection did not yield stable reply-log events).
- Manual in-app confirmation for reply compose/send remains the final interactive verification item.

## 11. Full-Fix Pass (Translation + Reply + Speed Monitoring) (2026-04-08)

### 11.1 Additional Root-Cause Fixes Applied
- Strengthened non-English target prompt behavior in `core/flash.py`:
  - removed target-agnostic copy-bias examples for non-English targets,
  - tightened instruction to avoid unchanged source output except proper nouns/already-target text.
- Increased runtime budgets to support reverse translation workloads:
  - `_SOFT_BUDGET_MS = 900`
  - `_HARD_BUDGET_MS = 1400`
  - `_ABS_BUDGET_MS = 2200`
  - `_ABS_BUDGET_MS_NON_ENG_TARGET = 3200`
- Improved lock-contention handling in translate path with longer lock wait and retry.
- Added explicit per-request speed/result logging in `core/flash.py`:
  - `[FLASH] OK src=... tgt=... profile=... model_ms=... total_ms=... chars=...`
  - `[FLASH] FALLBACK/UNCHANGED ...`
- Reduced reply-vs-clipboard contention in `main.py`:
  - pause `ClipboardMonitor` while reply composer is open,
  - auto-resume monitor when reply composer closes.

### 11.2 Validation Results
- Full test suite after final pass: **11/11 passed**.
- Rebuilt and reinstalled latest patched app successfully:
  - `installer/install_finalfix_2026-04-08.log` (`Installation process succeeded.`)

### 11.3 Installed-App Translation Speed Monitoring (Live)
- Observed from runtime log after fresh launch:
  - Korean sample: `model_ms=491`, `total_ms=494` -> translated card emitted.
  - Japanese sample: `model_ms=348`, `total_ms=348` -> translated card emitted.
- No fallback/unchanged suppression loop observed in this monitored pass for tested samples.

### 11.4 Reply Backend Verification
- Direct reverse-translation checks (same backend used by reply preview) now produce translated outputs for English -> Japanese test phrases instead of unchanged fallback.
- This confirms reply translation backend recovery; final user-facing confirmation remains manual UI interaction check (open reply, type, send).

## 12. Deep Analysis Outcome (Translation + UI) (2026-04-08)

### 12.1 Core Problems Identified
1. Reply-open side effect stalled translation pipeline:
- Clipboard monitor was being paused when reply opened; if reply remained open/unclosed, live translation cards stopped, which looked like app-wide failure.

2. Reply preview often returned unchanged source for non-English targets:
- Short English reply text frequently came back unchanged, causing preview/send path to appear broken.

3. Clipboard monitor failures could be silent:
- `pyperclip` read errors in monitor loop were effectively hidden at debug level, making capture failures hard to diagnose.

### 12.2 Fixes Applied
1. Removed reply-open global pause behavior in `main.py`:
- Reply no longer blocks clipboard translation pipeline.

2. Added strict non-English retry in `core/flash.py`:
- If non-English target output is unchanged, one strict target-language retry runs before fallback.

3. Added robust clipboard read fallback in `core/catch.py`:
- Primary: `pyperclip`.
- Fallback: Windows API `CF_UNICODETEXT` read.
- Visible warning logs every few seconds when reads fail.

4. Kept per-request speed/result logging in `core/flash.py` for active monitoring.

### 12.3 Validation Performed
- Automated tests: **11/11 passed** after final patches.
- Installed app live translation validation succeeded with fresh runtime logs:
  - multiple translated card outputs observed.
- Installed app speed monitoring (live sample):
  - average total latency about 565 ms (sampled run),
  - p95/max around 860 ms in sampled run.
- Headless UI-level reply preview test passed:
  - `ReplyBox` preview translated `hello` -> `こんにちは`.

### 12.4 Remaining Manual Check
- Final end-to-end manual reply send interaction (open reply, type, press send, verify copied target text in foreground app) should be confirmed once by user in interactive desktop flow.

## 13. SMaLL-100 Migration Kickoff (2026-04-11)

### 13.1 Step 1 Plan (Approved)
- Replace CT2 model directory references from NLLB CT2 folders to SMaLL-100 CT2 folder.
- Convert model with:

```bash
ct2-transformers-converter \
  --model alirezamsh/small100 \
  --output_dir models/small100-ct2 \
  --quantization int8
```

- Keep inference pipeline contract unchanged for this step:
  - same CTranslate2 inference call,
  - same tokenizer init path/logic,
  - same device placement behavior.

### 13.2 Step 1 Implementation Started
- Updated CT2 model config paths in `version.json`:
  - `flash.local_ct2_gpu_path` -> `models/small100-ct2`
  - `flash.local_ct2_cpu_path` -> `models/small100-ct2`
  - `flash.local_ct2_path` -> `models/small100-ct2`
- Updated unpacked packaging model payload path in `BabelGG_unpacked.spec`:
  - now includes `models/small100-ct2/` instead of `models/nllb-ct2-gpu/` and `models/nllb-ct2-cpu/`.
- Updated large binary ignore path in `.gitignore`:
  - `models/small100-ct2/model.bin`.
- Conversion run status:
  - Installed `ctranslate2`, `transformers`, and `sentencepiece` into `.venv`.
  - Started conversion using module entrypoint:
    - `d:/AbeSoft/BabelGG_v2/.venv/Scripts/python.exe -m ctranslate2.converters.transformers --model alirezamsh/small100 --output_dir models/small100-ct2 --quantization int8`
  - Current output folder `models/small100-ct2` is not present yet; conversion needs a clean rerun to completion.

### 13.3 Current Limitation Noted
- The active translation runtime in current branch is llama.cpp-based (`core/flash.py`).
- CT2 path updates are now aligned for migration, but full runtime switch to CT2-based translation flow remains a follow-up implementation step.

### 13.4 Validation Snapshot (2026-04-11)
- Verified conversion output directory exists: `models/small100-ct2/`.
- Verified key CT2 artifacts present:
  - `models/small100-ct2/model.bin`
  - `models/small100-ct2/config.json`
  - `models/small100-ct2/shared_vocabulary.json`
- Ran core automated suite: `tests/run_all.py` -> **11/11 passed**.
- Ran extended automated suite: `tests/run_all.py --extended` -> **12/12 passed**.
- No syntax/lint diagnostics were introduced in updated migration files.

## 14. SMaLL-100 Runtime Activation (Step 2) (2026-04-11)

### 14.1 Implementation
- Added optional CTranslate2 backend path inside `core/flash.py` while preserving existing routing/time-budget pipeline.
- Added runtime-aware model path resolution in `core/flash.py`:
  - CT2 runtime resolves directory model (`models/small100-ct2`).
  - llama runtime keeps GGUF model file behavior unchanged.
- Added CT2 initialization and tokenizer setup in `core/flash.py`:
  - `ctranslate2.Translator(...)`
  - `transformers.AutoTokenizer.from_pretrained(...)`
  - target-prefix handling for language-token steering.
- Activated CT2 runtime in `version.json`:
  - `flash.runtime` -> `ctranslate2`
  - `flash.repo` -> `alirezamsh/small100`

### 14.2 Validation
- Core suite: `tests/run_all.py` -> **11/11 passed**.
- Extended suite: `tests/run_all.py --extended` -> **12/12 passed**.
- No static diagnostics reported in edited runtime/config files.

### 14.3 Scope Guard
- Translation pipeline orchestration remains unchanged (timeouts, profile routing, fallback behavior).
- This step introduces backend switch support and activates CT2 via config without broad refactor.
