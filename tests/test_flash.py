import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.WARNING)

from core.flash import FlashEngine
import time

f = FlashEngine()
assert f.ready, 'FlashEngine must be ready after init'

# Test 1 — Japanese to English
r = f.translate('今日一緒にゲームしよう！', 'english')
assert r and r['translation'], 'Test 1 failed — no translation'
print(f'PASS  1  ja->en  {r["ms"]}ms  {r["translation"]}')

# Test 2 — Korean to English
r = f.translate('10분 후에 갈게', 'english')
assert r and r['translation'], 'Test 2 failed'
print(f'PASS  2  ko->en  {r["ms"]}ms  {r["translation"]}')

# Test 3 — Chinese to English
r = f.translate('快点！我们要输了！', 'english')
assert r and r['translation'], 'Test 3 failed'
print(f'PASS  3  zh->en  {r["ms"]}ms  {r["translation"]}')

# Test 4 — English to Japanese (reply direction)
r = f.translate('good game, well played', 'japanese')
assert r and r['translation'], 'Test 4 failed'
print(f'PASS  4  en->ja  {r["ms"]}ms  {r["translation"]}')

# Test 5 — English to English returns None
r = f.translate('hello world', 'english')
assert r is None, 'Test 5 failed — same language should return None'
print('PASS  5  same language returns None')

# Test 6 — Speed check (all under 5s after warmup)
texts = ['一百万人が感じたこと', '어려운 실력', 'السلام عليكم']
for t in texts:
    t0 = time.perf_counter()
    r  = f.translate(t, 'english')
    ms = (time.perf_counter() - t0) * 1000
    assert ms < 5000, f'Test 6 failed — too slow: {ms:.0f}ms'
    print(f'PASS  6  speed {ms:.0f}ms')
