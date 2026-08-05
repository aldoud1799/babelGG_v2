"""
trace_postproc.py — instrument the post-processing in translate() to find which step kills the translation.
Patches each method that could mutate or reject selected_translation.
"""
import sys, os, time
sys.path.insert(0, '.')
from core import flash as flash_mod

# Save originals
orig_generate_text_strict = flash_mod.FlashEngine._generate_text_strict_target
orig_repair_quotes = flash_mod.FlashEngine._repair_english_quoted_segments
orig_naturalize_module = sys.modules.get('core.natural')

# Track per-sentence state
CURRENT = [None]

def patched_generate_text_strict(self, text, tgt, max_tokens_override=None):
    if CURRENT[0]:
        CURRENT[0]['strict_target_called'] = True
        CURRENT[0]['strict_text'] = text
        CURRENT[0]['strict_tgt'] = tgt
    return orig_generate_text_strict(self, text, tgt, max_tokens_override)

def patched_repair_quotes(self, text):
    if CURRENT[0]:
        before = text
    out = orig_repair_quotes(self, text)
    if CURRENT[0]:
        CURRENT[0]['after_repair_quotes'] = out
        if before != out:
            CURRENT[0]['repair_quotes_changed'] = True
    return out

flash_mod.FlashEngine._generate_text_strict_target = patched_generate_text_strict
flash_mod.FlashEngine._repair_english_quoted_segments = patched_repair_quotes

# Patch naturalize if it exists
def patched_naturalize(text, translation):
    if CURRENT[0]:
        CURRENT[0]['naturalize_called'] = True
        CURRENT[0]['naturalize_input'] = translation
    # Call the real naturalize
    if orig_naturalize_module is not None:
        result = orig_naturalize_module.naturalize(text, translation)
    else:
        result = translation
    if CURRENT[0]:
        CURRENT[0]['naturalize_output'] = result
        if result != translation:
            CURRENT[0]['naturalize_changed'] = True
            CURRENT[0]['naturalize_from'] = translation
    return result

# Inject after loading
from core.flash import FlashEngine

print("Loading engine...")
engine = FlashEngine(device='cuda')

# Inject naturalize patch now that core.natural is importable
try:
    import core.natural
    core.natural.naturalize = patched_naturalize
    print(f"Patched core.natural.naturalize")
except ImportError:
    print("core.natural not available — naturalizer step will be a no-op")

# Warmup
print("Warming up...")
for _ in range(3):
    engine.translate("hello world", "english")
    engine.translate("Hola amigo", "english")

print(f"\n{'='*80}")
print("TESTING FAILED SENTENCES")
print(f"{'='*80}")

failed_sentences = [
    ("german", "Lasst uns heute zusammen spielen"),
    ("german", "Gut gespielt!"),
    ("german", "Hilfe, drei Feinde"),
    ("german", "Gewonnen!"),
    ("german", "Item teilen"),
    ("german", "Schau auf die Karte"),
    ("spanish", "Bien jugado!"),
    ("spanish", "Espera un momento"),
    ("spanish", "Mira el mapa"),
]

for src_lang, sent in failed_sentences:
    print(f"\n>>> {sent!r}")

    CURRENT[0] = {
        'sentence': sent,
        'strict_target_called': False,
        'repair_quotes_changed': False,
        'naturalize_called': False,
        'naturalize_changed': False,
    }

    result = engine.translate(sent, 'english')
    if result:
        print(f"  RESULT: OK -> {result['translation'][:60]!r}")
    else:
        print(f"  RESULT: NONE")

    state = CURRENT[0]
    if state['strict_target_called']:
        print(f"  STRICT_RETRY fired for {state.get('strict_tgt')!r} — surprising for English target!")
    if state['repair_quotes_changed']:
        print(f"  repair_english_quoted_segments changed the output")
    if state['naturalize_changed']:
        print(f"  naturalize changed: from={state['naturalize_from'][:60]!r} to={state['naturalize_output'][:60]!r}")
    elif state['naturalize_called']:
        print(f"  naturalize called but no change")

print(f"\n{'='*80}")
print("DONE")
print(f"{'='*80}")