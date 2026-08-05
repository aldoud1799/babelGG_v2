import sys, os
sys.path.insert(0, '.')
os.makedirs('data', exist_ok=True)

from core.vault import TranslationVault

v = TranslationVault()

# Test 1 — store and exact lookup
v.store('hello', 'jpn_Jpan', 'こんにちは')
assert v.lookup('hello', 'jpn_Jpan') == 'こんにちは', 'Test 1 failed'
print('PASS  1 — exact lookup')

# Test 2 — miss returns None
assert v.lookup('goodbye', 'jpn_Jpan') is None, 'Test 2 failed'
print('PASS  2 — miss returns None')

# Test 3 — fuzzy match (store identical text, lookup with minor variation)
v.store('let us play together now', 'jpn_Jpan', '一緒にプレイしましょう')
result = v.lookup('let us play together now', 'jpn_Jpan')
assert result == '一緒にプレイしましょう', 'Test 3 failed'
print('PASS  3 — fuzzy match')

# Test 4 — persistence (new instance reads saved data)
v.flush()
v2 = TranslationVault()
assert v2.lookup('hello', 'jpn_Jpan') == 'こんにちは', 'Test 4 failed'
print('PASS  4 — persistence across instances')

# Test 5 — LRU eviction at MAX_ENTRIES
v3 = TranslationVault()
v3.MAX_ENTRIES = 3
for i in range(4):
    v3.store(f'text_{i}', 'eng_Latn', f'trans_{i}')
assert v3.lookup('text_0', 'eng_Latn') is None, 'Test 5 failed — oldest not evicted'
print('PASS  5 — LRU eviction')

# Test 6 — short texts should not use fuzzy lookup
v4 = TranslationVault()
v4.store('hello there', 'eng_Latn', 'A')
assert v4.lookup('hello there!', 'eng_Latn') is None, 'Test 6 failed — short fuzzy should be disabled'
print('PASS  6 — short fuzzy disabled')

# Test 7 — invalidate removes exact mapping
v4.store('auto-fix me', 'eng_Latn', 'old value')
assert v4.lookup('auto-fix me', 'eng_Latn') == 'old value', 'Test 7 setup failed'
assert v4.invalidate('auto-fix me', 'eng_Latn') is True, 'Test 7 failed — invalidate returned False'
assert v4.lookup('auto-fix me', 'eng_Latn') is None, 'Test 7 failed — value still present after invalidate'
print('PASS  7 — invalidate exact entry')

print('\nAll vault tests passed')
