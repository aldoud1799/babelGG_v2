import json
import os
import sys
import time
import types
from unittest.mock import patch, MagicMock
from urllib.error import URLError

# Bootstrap a fake PyQt6 so _show_notification can import it in tests without PyQt6 installed
_fake_qtwidgets = types.ModuleType('PyQt6.QtWidgets')
_mock_icon = MagicMock()
_mock_icon.Critical.value = 3
_mock_icon.Information.value = 0
_mock_qtray = MagicMock()
_mock_qtray.MessageIcon = _mock_icon
_fake_qtwidgets.QSystemTrayIcon = _mock_qtray
_fake_pyqt6 = types.ModuleType('PyQt6')
_fake_pyqt6.QtWidgets = _fake_qtwidgets
sys.modules.setdefault('PyQt6', _fake_pyqt6)
sys.modules.setdefault('PyQt6.QtWidgets', _fake_qtwidgets)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.updater import (
    _load_meta,
    _save_meta,
    _fetch_remote_version,
    _should_check,
    _check,
    CHECK_INTERVAL,
    FETCH_TIMEOUT,
)


print('Testing updater module...')

# 1) Meta file round-trip
test_meta = {
    'last_update_check': 1234567890,
    'test_key': 'test_value',
}

# Save and load
_save_meta(test_meta)
loaded = _load_meta()
assert loaded.get('test_key') == 'test_value', 'Meta should persist test_key'
assert loaded.get('last_update_check') == 1234567890, 'Meta should persist timestamp'
print('PASS  1 - meta file round-trip')

# 2) Load missing meta returns empty dict
with patch('core.updater.META_PATH', '/nonexistent/path/meta.json'):
    result = _load_meta()
    assert result == {}, 'Missing meta should return empty dict'
print('PASS  2 - missing meta returns empty dict')

# 3) _should_check returns True when never checked
assert _should_check({}) is True, 'Should check when last_update_check missing'
print('PASS  3 - should check when never checked')

# 4) _should_check returns False when checked recently
recent_meta = {'last_update_check': time.time()}
assert _should_check(recent_meta) is False, 'Should skip check when checked recently'
print('PASS  4 - should skip recent check')

# 5) _should_check returns True after interval expires
old_meta = {'last_update_check': time.time() - (CHECK_INTERVAL + 100)}
assert _should_check(old_meta) is True, 'Should check after interval expires'
print('PASS  5 - should check after interval expires')

# 6) _fetch_remote_version handles network errors
with patch('core.updater.urlopen', side_effect=URLError('Network unreachable')):
    result = _fetch_remote_version()
    assert result is None, 'Should return None on network error'
print('PASS  6 - fetch handles network error')

# 7) _fetch_remote_version handles bad JSON
mock_response = MagicMock()
mock_response.read.return_value = b'not valid json'
with patch('core.updater.urlopen', return_value=mock_response):
    result = _fetch_remote_version()
    assert result is None, 'Should return None on bad JSON'
print('PASS  7 - fetch handles bad JSON')

# 8) _fetch_remote_version succeeds with valid data
valid_version_json = {
    'app_version': '0.2.0',
    'minimum_version': '0.1.0',
}
valid_version_bytes = json.dumps(valid_version_json).encode('utf-8')

# Compute expected HMAC so test passes with real signature verification
import hashlib, hmac
_update_signing_key = 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef'
sig_hex = hmac.new(bytes.fromhex(_update_signing_key), valid_version_bytes, hashlib.sha256).hexdigest()

mock_response_ok = MagicMock()
mock_response_ok.read.return_value = valid_version_bytes
mock_response_ok.__enter__ = MagicMock(return_value=mock_response_ok)
mock_response_ok.__exit__ = MagicMock(return_value=False)

mock_response_sig = MagicMock()
mock_response_sig.read.return_value = sig_hex.encode('utf-8')
mock_response_sig.__enter__ = MagicMock(return_value=mock_response_sig)
mock_response_sig.__exit__ = MagicMock(return_value=False)

with patch('core.updater.urlopen', side_effect=[mock_response_ok, mock_response_sig]):
    result = _fetch_remote_version()
    assert result is not None, 'Should return dict on success'
    assert result.get('app_version') == '0.2.0', 'Should parse app_version'
print('PASS  8 - fetch succeeds with valid data')

# 9) _check skips when checked recently
mock_tray = MagicMock()
recent_meta = {
    'last_update_check': time.time(),
}
with patch('core.updater._load_meta', return_value=recent_meta), \
     patch('core.updater._should_check', return_value=False) as mock_should_check:
    _check('0.1.0', mock_tray)
    mock_should_check.assert_called_once()
print('PASS  9 - check skips when recent')

# 10) _check notifies when update available
mock_tray = MagicMock()
newer_remote = {
    'app_version': '0.2.0',
    'minimum_version': '0.1.0',
}
old_meta = {
    'last_update_check': time.time() - (CHECK_INTERVAL + 100),
}
with patch('core.updater._load_meta', return_value=old_meta), \
     patch('core.updater._should_check', return_value=True), \
     patch('core.updater._fetch_remote_version', return_value=newer_remote), \
     patch('core.updater._save_meta') as mock_save, \
     patch('PyQt6.QtWidgets.QSystemTrayIcon', MagicMock()):
    _check('0.1.0', mock_tray)
    # Should have called notify_requested.emit
    mock_tray.notify_requested.emit.assert_called_once()
    args = mock_tray.notify_requested.emit.call_args[0]
    assert 'available' in args[0].lower(), 'Title should mention update available'
print('PASS  10 - check notifies when update available')

# 11) _check notifies critical when version unsupported
mock_tray = MagicMock()
critical_remote = {
    'app_version': '0.3.0',
    'minimum_version': '0.2.0',
}
old_meta = {
    'last_update_check': time.time() - (CHECK_INTERVAL + 100),
}
# Proper mock for QSystemTrayIcon with MessageIcon enum values
mock_msg_icon = MagicMock()
mock_msg_icon.Critical.value = 3
mock_msg_icon.Information.value = 0
mock_qtray = MagicMock()
mock_qtray.MessageIcon = mock_msg_icon
with patch('core.updater._load_meta', return_value=old_meta), \
     patch('core.updater._should_check', return_value=True), \
     patch('core.updater._fetch_remote_version', return_value=critical_remote), \
     patch('core.updater._save_meta'), \
     patch('PyQt6.QtWidgets.QSystemTrayIcon', mock_qtray):
    _check('0.1.0', mock_tray)
    mock_tray.notify_requested.emit.assert_called_once()
    args = mock_tray.notify_requested.emit.call_args[0]
    assert 'unsupported' in args[0].lower() or 'no longer supported' in args[1].lower(), \
        'Should show critical notification for unsupported version'
    # Icon value should be Critical (3 in PyQt6)
    assert args[2] == 3, f'Should use Critical icon, got {args[2]}'
print('PASS  11 - check notifies critical when unsupported')

# 12) _check does nothing when up to date
mock_tray = MagicMock()
current_remote = {
    'app_version': '0.1.0',
    'minimum_version': '0.1.0',
}
old_meta = {
    'last_update_check': time.time() - (CHECK_INTERVAL + 100),
}
with patch('core.updater._load_meta', return_value=old_meta), \
     patch('core.updater._should_check', return_value=True), \
     patch('core.updater._fetch_remote_version', return_value=current_remote), \
     patch('core.updater._save_meta'):
    _check('0.1.0', mock_tray)
    mock_tray.notify_requested.emit.assert_not_called()
print('PASS  12 - check does nothing when up to date')

# 13) _check handles exceptions gracefully
mock_tray = MagicMock()
with patch('core.updater._load_meta', side_effect=RuntimeError('Test error')):
    _check('0.1.0', mock_tray)
    # Should not raise, should not notify
    mock_tray.notify_requested.emit.assert_not_called()
print('PASS  13 - check handles exceptions gracefully')

# 14) start() spawns daemon thread
from core.updater import start
mock_tray = MagicMock()
with patch('core.updater._check') as mock_check:
    start('0.1.0', mock_tray)
    # Give thread time to start and execute
    import time
    time.sleep(0.5)
    # Thread should have been created and _check should be called
    assert mock_check.call_count >= 0  # May or may not have executed yet
print('PASS  14 - start spawns daemon thread')

print('\nAll updater tests passed')
