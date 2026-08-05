"""
trace_gen.py — call _generate_with_timeout and _generate_text directly
for failing sentences to see what they actually return.
"""
import sys, os, time
sys.path.insert(0, '.')
from core.flash import FlashEngine

engine = FlashEngine(device='cuda')
print(f"Ready: profile={engine._profile}")

# Warmup
for _ in range(2):
    engine.translate("hello world", "english")
    engine.translate("Hola amigo", "english")

failed_sentences = [
    ("german", "Lasst uns heute zusammen spielen"),
    ("german", "Gut gespielt!"),
    ("german", "Hilfe, drei Feinde"),
    ("german", "Gewonnen!"),
    ("spanish", "Bien jugado!"),
    ("spanish", "Espera un momento"),
    ("spanish", "Mira el mapa"),
]

print(f"\n{'='*80}")
print("Direct calls to _generate_with_timeout / _generate_text")
print(f"{'='*80}")

for src_lang, sent in failed_sentences:
    print(f"\n>>> {sent!r}")
    # Direct generate_text call
    out = engine._generate_text(sent, 'eng_Latn')
    print(f"  _generate_text direct: {out!r}")
    # Generate with timeout
    out2, timed_out, err = engine._generate_with_timeout(sent, 'eng_Latn', 1600)
    print(f"  _generate_with_timeout: timed_out={timed_out}, err={err!r}, out={out2!r}")