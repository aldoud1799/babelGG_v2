"""
Full end-to-end pipeline test: CATCH -> SLANG -> FLASH
Verifies translations fire when foreign text is copied, and are suppressed for URLs/English.
"""
import logging, sys, time, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

import pyperclip
from core.flash import FlashEngine
from core.catch import ClipboardMonitor

print('=' * 60)
print('  BabelGG End-to-End Pipeline Test')
print('=' * 60)

print('\nLoading FlashEngine...')
f = FlashEngine(device='cuda')
if not f.ready:
    print('CUDA failed, falling back to CPU...')
    f = FlashEngine(device='cpu')
assert f.ready, 'FlashEngine failed to load!'
print(f'FlashEngine ready on {f.device}')

results = []
monitor = ClipboardMonitor(f, callback=results.append)
pyperclip.copy('')
monitor._last = ''
monitor.start()
time.sleep(0.7)

# ── Test 1 — Japanese ────────────────────────────────────────────────────────
pyperclip.copy('今日一緒にゲームしよう！')
print('\nTest 1: Copied Japanese text, waiting for translation...')
time.sleep(8)
assert len(results) >= 1, 'FAIL Test 1 — no result for Japanese text'
r = results[-1]
print(f'PASS 1  [{r["src_lang"][:3].upper()}] {r["original"]}')
print(f'        -> {r["translation"]}  ({r["ms"]}ms)')

# ── Test 2 — Korean ──────────────────────────────────────────────────────────
pyperclip.copy('10분 후에 갈게')
print('\nTest 2: Copied Korean text, waiting...')
time.sleep(8)
assert len(results) >= 2, 'FAIL Test 2 — no result for Korean text'
r = results[-1]
print(f'PASS 2  [{r["src_lang"][:3].upper()}] {r["original"]}')
print(f'        -> {r["translation"]}  ({r["ms"]}ms)')

# ── Test 3 — Chinese ─────────────────────────────────────────────────────────
pyperclip.copy('快点！我们要输了！')
print('\nTest 3: Copied Chinese text, waiting...')
time.sleep(8)
assert len(results) >= 3, 'FAIL Test 3 — no result for Chinese text'
r = results[-1]
print(f'PASS 3  [{r["src_lang"][:3].upper()}] {r["original"]}')
print(f'        -> {r["translation"]}  ({r["ms"]}ms)')

# ── Test 4 — URL rejected ────────────────────────────────────────────────────
count = len(results)
pyperclip.copy('https://google.com')
time.sleep(1.5)
assert len(results) == count, 'FAIL Test 4 — URL should not trigger card'
print('\nPASS 4  URL rejected correctly')

# ── Test 5 — English rejected ─────────────────────────────────────────────────
pyperclip.copy('hello this is english text')
time.sleep(1.5)
assert len(results) == count, 'FAIL Test 5 — English should not trigger card'
print('PASS 5  English rejected correctly')

# ── Test 6 — Slang normalization ──────────────────────────────────────────────
# gg ez are english slang, should NOT trigger the foreign detector
pyperclip.copy('gg ez lmao')
time.sleep(1.5)
assert len(results) == count, 'FAIL Test 6 — slang should not trigger card'
print('PASS 6  English slang rejected correctly')

monitor.stop()
print(f'\n{"=" * 60}')
print(f'  ALL TESTS PASSED  ({len(results)} translations produced)')
print(f'{"=" * 60}')
