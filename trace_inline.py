"""
trace_inline.py — copy the translate() flow into a trace wrapper that prints every state change.
"""
import sys, os, time
sys.path.insert(0, '.')
from core.flash import FlashEngine

engine = FlashEngine(device='cuda')
print(f"Ready: profile={engine._profile}")

# Warmup
for _ in range(3):
    engine.translate("hello", "english")
    engine.translate("Hola", "english")


def trace_translate(text, tgt_lang):
    """Re-implement translate() with prints at every state transition."""
    print(f"\n>>> {text!r} -> {tgt_lang!r}")
    if not text or not text.strip():
        return None
    if not engine.ready:
        return None

    text = text.strip()
    tgt = engine.LANG_CODES.get(str(tgt_lang or 'english').lower(), 'eng_Latn')
    src = engine.detect_lang(text)
    print(f"    src={src}, tgt={tgt}")

    if src == tgt:
        return None

    budget_ms = engine._ABS_BUDGET_MS if tgt == 'eng_Latn' else engine._ABS_BUDGET_MS_NON_ENG_TARGET
    extra_chars = max(0, len(text) - 120)
    if extra_chars:
        budget_ms += extra_chars * 35
    if engine.device == 'cpu':
        budget_ms = max(budget_ms, 15000)
    request_budget_ms = budget_ms
    request_deadline = time.perf_counter() + (budget_ms / 1000.0)
    print(f"    budget={budget_ms}ms")

    selected_translation = ''
    selected_ms = 0
    selected_profile = 'fallback'

    profiles = engine._recommended_profiles()
    print(f"    profiles: {profiles}")

    for profile in profiles:
        remaining_before = engine._remaining_budget_ms(request_deadline)
        if remaining_before <= 0:
            print(f"    [{profile}] remaining<=0, breaking")
            break

        if profile == 'fallback':
            out = engine._deterministic_fallback(text, tgt)
            elapsed = round((time.perf_counter() - time.perf_counter()) * 1000)
            selected_translation = out or ''
            selected_ms = elapsed
            selected_profile = profile
            print(f"    [{profile}] fallback -> out={out!r}")
            break

        if remaining_before < engine._MIN_ATTEMPT_BUDGET_MS:
            print(f"    [{profile}] remaining<MIN, continue")
            continue

        acquired = False
        for attempt in (1, 2):
            lock_timeout = min(1.2, max(0.12, engine._remaining_budget_ms(request_deadline) / 1000.0))
            acquired = engine._lock.acquire(timeout=lock_timeout)
            if acquired:
                break
            if attempt == 1 and engine._remaining_budget_ms(request_deadline) > 180:
                time.sleep(0.05)
        if not acquired:
            elapsed = round((time.perf_counter() - time.perf_counter()) * 1000)
            print(f"    [{profile}] lock contention")
            continue

        try:
            if not engine._ensure_profile(profile):
                print(f"    [{profile}] ensure_profile FAILED")
                continue
        finally:
            engine._lock.release()

        remaining_after_init = engine._remaining_budget_ms(request_deadline)
        out, timed_out, err = engine._generate_with_timeout(text, tgt, remaining_after_init)
        print(f"    [{profile}] gen: timed_out={timed_out} err={err!r} out={out!r}")

        if timed_out:
            print(f"    [{profile}] timed out, continue")
            continue
        if err is not None:
            print(f"    [{profile}] error: {err}")
            raise err

        elapsed = round((time.perf_counter() - time.perf_counter()) * 1000)
        ok = bool(out and out.strip())
        print(f"    [{profile}] ok={ok}")

        if ok:
            selected_translation = out.strip()
            selected_ms = elapsed
            selected_profile = profile
            print(f"    [{profile}] SELECTED: {selected_translation!r}")
            break

    print(f"    -- post-loop selected_translation={selected_translation!r} --")

    if not selected_translation:
        fallback = engine._deterministic_fallback(text, tgt)
        if fallback:
            selected_translation = fallback
        else:
            print(f"    ALL FAILED -> return None")
            return None

    # Pathological check
    if tgt == 'eng_Latn' and engine._is_pathological_translation(selected_translation, tgt):
        print(f"    PATHOLOGICAL")
        recovered = engine._segment_translate_retry(text, tgt, request_deadline)
        if recovered and not engine._is_pathological_translation(recovered, tgt):
            selected_translation = recovered.strip()
            print(f"    recovered from pathological: {selected_translation!r}")

    # Strict retry for non-English (skipped for English)
    if src != tgt and tgt != 'eng_Latn':
        pass

    # needs_repair check
    if src != tgt:
        needs_repair = engine._is_near_unchanged_output(text, selected_translation)
        print(f"    needs_repair={needs_repair} (selected={selected_translation[:60]!r})")

    # Final return
    if selected_translation:
        return {
            'original': text,
            'translation': selected_translation,
            'src_lang': src,
            'tgt_lang': tgt,
            'ms': selected_ms,
            'profile': selected_profile,
        }
    return None


# Test failed and successful sentences
tests = [
    ("Gewonnen!", "english"),  # known fails
    ("Schau auf die Karte", "english"),  # known fails
    ("Hilfe, drei Feinde", "english"),  # known fails
    ("Danke", "english"),  # known works
    ("Nächste Runde", "english"),  # known works
    ("Bien jugado!", "english"),  # known fails
    ("Gracias", "english"),  # known works
]

for text, tgt in tests:
    result = trace_translate(text, tgt)
    if result:
        print(f"  -> OK: {result['translation'][:60]!r}")
    else:
        print(f"  -> NONE")