"""
trace_real.py — call REAL translate() 5 times in a row on each test sentence.
The benchmark shows high failure rates that vary by sentence. Let me see if
the failures are state-dependent (e.g. profile cooldown, slow_streak).
"""
import sys, os, time
sys.path.insert(0, '.')
from core.flash import FlashEngine

print("Loading GPU engine...")
engine = FlashEngine(device='cuda')
print(f"ready={engine.ready}, profile={engine._profile}")

# Run the full benchmark corpus for German and Spanish, 5 runs each
test_pairs = [
    ("german", "english", [
        "Lasst uns heute zusammen spielen", "Gut gespielt!", "Hilfe, drei Feinde",
        "Warte kurz", "Danke", "Nochmal", "Sorry, bin spät", "Gewonnen!",
        "Dieser Boss ist zu stark", "Nächste Runde", "Item teilen", "Team ist schwach",
        "Feind erledigt", "Schau auf die Karte", "Kann nicht chatten", "Nachladen",
        "Deckung", "Position halten", "Wenig Leben", "Mach ich allein",
    ]),
    ("spanish", "english", [
        "Jugamos juntos hoy", "Bien jugado!", "Ayuda, hay tres enemigos",
        "Espera un momento", "Gracias", "Otra vez", "Perdón, llegué tarde",
        "Ganamos!", "Este jefe es muy fuerte", "Siguiente ronda",
        "Comparte el objeto", "El equipo es débil", "Maté al enemigo",
        "Mira el mapa", "No puedo chatear", "Recarga", "Tapa",
        "Toma posición", "Casi sin vida", "Lo hago solo",
    ]),
]

# Patch translate() to log what's happening
original_translate = FlashEngine.translate
WARMUP_DONE = [False]

def patched_translate(self, text, tgt_language='english'):
    result = original_translate(self, text, tgt_language)
    if not WARMUP_DONE[0]:
        # Skip first 2 results as warmup
        WARMUP_DONE[0] = True
        return result
    return result

FlashEngine.translate = patched_translate

# Warmup
print("\nWarming up...")
for _ in range(3):
    engine.translate("hello", "english")
    engine.translate("Hola", "english")

# Now reset counter and run real test
WARMUP_DONE[0] = False
results = []
for src_lang, tgt_lang, sentences in test_pairs:
    print(f"\n=== {src_lang} -> {tgt_lang} ===")
    pair_results = []
    for sent in sentences:
        per_run = []
        for run in range(5):
            t0 = time.perf_counter()
            r = original_translate(engine, sent, tgt_lang)
            elapsed = round((time.perf_counter()-t0)*1000)
            per_run.append((r, elapsed))
        # Aggregate per sentence
        successes = [e for r, e in per_run if r]
        failures = len(per_run) - len(successes)
        avg_ms = round(sum(successes)/len(successes), 1) if successes else None
        first_translation = next((r['translation'] for r, _ in per_run if r), None)
        print(f"  {sent!r:<45} fails={failures}/5 avg_ms={avg_ms}")
        if first_translation:
            print(f"      first: {first_translation[:60]!r}")
        pair_results.append({'sentence': sent, 'failures': failures, 'avg_ms': avg_ms, 'first': first_translation})
    results.append((f"{src_lang}->{tgt_lang}", pair_results))

print(f"\n=== SUMMARY ===")
for pair_key, pair_results in results:
    total_failures = sum(r['failures'] for r in pair_results)
    total_attempts = len(pair_results) * 5
    print(f"{pair_key}: {total_failures}/{total_attempts} = {total_failures/total_attempts*100:.0f}% failure rate")