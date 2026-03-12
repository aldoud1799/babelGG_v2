import sys, os, time
sys.path.insert(0, '.')

import pyperclip
from unittest.mock import MagicMock
from core.catch import ClipboardMonitor

results = []
flash   = MagicMock()
flash.translate.return_value = {
    'original':    'test',
    'translation': 'テスト',
    'src_lang':    'eng_Latn',
    'tgt_lang':    'jpn_Jpan',
    'ms':          120,
}

monitor = ClipboardMonitor(flash, callback=results.append)

# Clear clipboard and pre-seed _last to avoid stale content triggering a result
pyperclip.copy('')
monitor._last = ''
monitor.start()
time.sleep(0.7)  # let first poll see the empty clipboard

# Test 1 — foreign text triggers callback
pyperclip.copy('今日一緒にゲームしよう！')
time.sleep(1.2)
assert len(results) == 1, f'Test 1 failed — expected 1 result, got {len(results)}'
print('PASS  1 — foreign text triggers callback')

# Test 2 — URL is rejected
pyperclip.copy('https://google.com')
time.sleep(1.2)
assert len(results) == 1, 'Test 2 failed — URL should not trigger callback'
print('PASS  2 — URL rejected')

# Test 3 — English text is rejected
pyperclip.copy('hello world this is english text')
time.sleep(1.2)
assert len(results) == 1, 'Test 3 failed — English should not trigger callback'
print('PASS  3 — English rejected')

monitor.stop()
print('\nAll catch tests passed')
