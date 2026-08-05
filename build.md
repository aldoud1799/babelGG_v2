# BabelGG LLM Backend Build Plan

Date: 2026-04-06
Scope: Replace CT2 translation path with a llama-cpp Vulkan-first, adaptive multi-path router that prioritizes game stability and sub-400ms user-perceived latency.

## 0. To-Do Checklist

- [x] Create implementation plan file.
- [x] Replace CT2 backend with llama-cpp adaptive router.
- [x] Enforce required generation prompt and decoding settings.
- [x] Add regex post-parse safety fallback for `<t>...</t>` output.
- [x] Remove CT2 startup preload dependency from app boot path.
- [x] Add `llama-cpp-python` dependency to requirements.
- [x] Update model setup script to download GGUF model.
- [x] Install `llama-cpp-python` in `.venv` with Vulkan-enabled build.
- [x] Verify model file exists at `models/qwen2.5-1.5b-instruct-q4_k_m.gguf`.
- [x] Run smoke translation test (ja/ko/zh -> en and en -> ja).
- [x] Run full test suite and capture regressions.
- [x] Tune profile thresholds from observed p50/p95 latencies.
- [x] Final packaging validation (PyInstaller + startup/runtime checks).

## 1. Goals

- Keep translation fast and predictable for gaming chat.
- Prevent game instability (no blocking stalls, graceful fallback on failures).
- Control memory growth over time (strict context and capped decode budget).
- Preserve output contract: return translation only, no explanations.

## 2. Hard Requirements (v1)

- Model runtime: `llama-cpp-python` (Vulkan build).
- Model file: `qwen2.5-1.5b-instruct-q4_k_m.gguf`.
- Base init settings:
  - `n_gpu_layers = -1`
  - `n_ctx = 256`
  - `verbose = False`
- Generation settings:
  - `max_tokens = 60`
  - `temperature = 0.1`
  - `stop = ["<|im_end|>", "</t>", "\n\n"]`
- Prompt contract:
  - strict ChatML with `<|im_start|>` and `<|im_end|>` markers
  - required system message
  - 3 few-shot examples enforcing `<t>...</t>` output
- Post-parse safety net:
  - regex extraction for `<t>...</t>`
  - malformed/missing tags -> sanitize and fallback
  - suspiciously long/hallucinated output -> return original input

## 3. Adaptive Multi-Path Strategy

### Path A (Primary GPU)

- Full offload (`n_gpu_layers=-1`) on capable hardware.
- Tight deadline budget for fast completion.

### Path B (Constrained GPU)

- Reduced GPU layers when latency/VRAM issues appear.
- Same prompt and output contract.

### Path C (CPU-safe LLM)

- CPU inference as compatibility fallback.
- Strict timeout and immediate return on budget breach.

### Path D (Deterministic fallback)

- Phrase/slang map + rule-based minimal translator fallback.
- Always returns quickly and never blocks the game loop.

## 4. Routing and Deadlines

- Message budget policy:
  - soft deadline: 280ms
  - hard deadline: 380ms
  - absolute cap: 400ms
- Per-request routing factors:
  - text length
  - prior recent path performance in session
  - recent timeout/error rate

## 5. Failure Handling

- Initialization errors: disable path and degrade to next path.
- Generation timeout: cancel/degrade immediately.
- Parse/output violations: sanitize/degrade.
- Repeated failures: auto-downgrade runtime tier.

## 6. Implementation Phases

### Phase 1: Core Engine Swap

- Add llama-cpp engine wrapper and singleton initialization.
- Add strict ChatML prompt builder + few-shot examples.
- Add generation wrapper with required decoding config.
- Add regex-based output parser and fallback sanitizer.

### Phase 2: Router Layer

- Add path router (A/B/C/D) and request deadline enforcement.
- Add per-session rolling metrics (latency, timeout, parse failures).
- Add auto-downgrade and cautious auto-upgrade heuristics.

### Phase 3: Integration and Config

- Wire router into existing translation entry point.
- Add config flags in `config.json` for mode selection and thresholds.
- Keep default mode as adaptive balanced.

### Phase 4: Validation

- Functional tests:
  - slang/formal/emoji/noisy OCR cases
  - missing-tag and hallucination fallback behavior
- Performance tests:
  - p50/p95 latency by hardware tier
  - long-session memory stability checks
- Reliability tests:
  - GPU unavailable/driver failure handling
  - repeated timeout degradation behavior

## 7. Deliverables

- Updated translation backend module (drop-in compatible).
- New adaptive router and parser utilities.
- Config defaults and migration-safe toggles.
- Test updates for parser, fallback, and routing behaviors.

## 8. Acceptance Criteria

- No crash regressions in translation pipeline.
- Output always a single translation string (or safe fallback), no assistant chatter.
- Stable memory footprint during extended play sessions.
- Meets target latency envelope on supported GPUs; predictable degradation elsewhere.

## 9. Rollout

- Stage 1: internal dogfood with telemetry enabled.
- Stage 2: limited beta with compatibility mode fallback.
- Stage 3: default adaptive mode for all users.
