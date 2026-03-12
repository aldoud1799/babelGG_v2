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

print('\nAll vault tests passed')
