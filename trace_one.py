"""
trace_one.py — instrument FlashEngine.translate() to see exactly where it returns None.
Calls translate() with a German sentence known to fail, captures what happens at each stage.
"""
import sys, os
sys.path.insert(0, '.')
import time

from core.flash import FlashEngine

# Monkey-patch critical methods to log what they return
original_translate = FlashEngine.translate

def patched_translate(self, text, tgt_language='english'):
    """Wrap translate() and log what comes back from each stage."""
    print(f"\n>>> translate({text!r}, {tgt_language!r})", flush=True)

    if not text or not text.strip():
        print("    empty text, returning None")
        return None
    if not self.ready:
        print("    engine not ready, returning None")
        return None

    text = text.strip()
    tgt = self.LANG_CODES.get(str(tgt_language or 'english').lower(), 'eng_Latn')
    src = self.detect_lang(text)
    print(f"    src={src}, tgt={tgt}, src!=tgt={src != tgt}")

    # Replicate the profile loop with full instrumentation
    request_deadline = time.perf_counter() + 1.6  # _ABS_BUDGET_MS

    profiles = self._recommended_profiles()
    print(f"    recommended_profiles: {profiles}")

    for profile in profiles:
        if profile == 'fallback':
            print(f"    -- profile {profile} (skip detailed trace) --")
            continue
        remaining_before = self._remaining_budget_ms(request_deadline)
        print(f"    -- profile {profile}, remaining={remaining_before}ms --")

        if remaining_before <= 0:
            print(f"    remaining <= 0, breaking")
            break
        if remaining_before < self._MIN_ATTEMPT_BUDGET_MS:
            print(f"    remaining < MIN_ATTEMPT_BUDGET_MS, continue")
            continue

        # Profile ensure
        t0 = time.perf_counter()
        if not self._ensure_profile(profile):
            print(f"    ensure_profile failed")
            continue
        print(f"    ensure_profile ok ({round((time.perf_counter()-t0)*1000)}ms)")

        # Generate
        remaining_after_init = self._remaining_budget_ms(request_deadline)
        print(f"    remaining_after_init={remaining_after_init}ms")
        out, timed_out, err = self._generate_with_timeout(text, tgt, remaining_after_init)
        print(f"    _generate_with_timeout returned: timed_out={timed_out}, err={err}, out={out!r}")

        if timed_out:
            print(f"    timed out, continuing to next profile")
            continue
        if err:
            print(f"    error: {err}")
            raise err

        if out and out.strip():
            print(f"    SUCCESS out={out!r}")
            return {
                'original': text,
                'translation': out.strip(),
                'src_lang': src,
                'tgt_lang': tgt,
                'ms': 0,
                'cache_hit': False,
                'phrase_hit': False,
                'naturalizer_applied': False,
            }
        else:
            print(f"    out empty")

    print(f"    exhausted all profiles, returning None (no selected_translation)")
    return None


FlashEngine.translate = patched_translate

# Load engine and test
engine = FlashEngine(device='cuda')
print(f"\nLoaded: ready={engine.ready}, profile={engine._profile}")

# Test sentences known to fail
test_sentences = [
    ("german", "Hilfe, drei Feinde"),
    ("german", "Schau auf die Karte"),
    ("german", "Gewonnen!"),
    ("spanish", "Bien jugado!"),
    ("spanish", "Espera un momento"),
]

for lang, sent in test_sentences:
    result = engine.translate(sent, 'english')
    print(f"  RESULT for {sent!r}: {'OK' if result else 'NONE'}")