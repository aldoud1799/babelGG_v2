import sys
sys.path.insert(0, '.')

from core.slang import normalize, normalize_for_translation, lookup

# Test 1 — basic substitution
assert 'good game' in normalize('gg'), 'Test 1 failed'
print('PASS  1  gg -> good game')

# Test 2 — multi-word phrase matches before single word
r = normalize('gg ez')
assert 'easy' in r, 'Test 2 failed'
print(f'PASS  2  gg ez -> {r}')

# Test 3 — case insensitive
assert normalize('GG') == normalize('gg'), 'Test 3 failed'
print('PASS  3  case insensitive')

# Test 4 — non-slang unchanged
t = 'hello how are you'
assert normalize(t) == t, 'Test 4 failed'
print('PASS  4  non-slang unchanged')

# Test 5 — was_changed flag
_, changed   = normalize_for_translation('gg wp')
assert changed is True, 'Test 5a failed'
_, no_change = normalize_for_translation('hello')
assert no_change is False, 'Test 5b failed'
print('PASS  5  was_changed flag')

# Test 6 — direct lookup
assert lookup('gg') == 'good game', 'Test 6 failed'
assert lookup('UNKNOWN') is None,   'Test 6b failed'
print('PASS  6  direct lookup')

import core.slang as _s
print(f'\nAll slang tests passed ({len(_s._SLANG)} terms in dictionary)')
