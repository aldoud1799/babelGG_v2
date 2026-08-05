import json
import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.license import LicenseManager


class _Resp:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _install_fake_requests(mode: str):
    def post(url, json=None, headers=None, timeout=10):
        if mode == 'invalid' and url.endswith('/activate'):
            return _Resp(400, {'error': 'Invalid license key'})
        if mode == 'valid' and url.endswith('/activate'):
            return _Resp(200, {
                'activated': True,
                'license_key': {'product_name': 'Pro Lifetime'},
                'instance': {'id': 'instance-123', 'meta': {'customer_email': 'user@example.com'}},
            })
        if url.endswith('/validate'):
            return _Resp(200, {'valid': True})
        if url.endswith('/deactivate'):
            return _Resp(200, {'deactivated': True})
        return _Resp(500, {'error': 'unexpected'})

    sys.modules['requests'] = SimpleNamespace(post=post)


tmp_dir = tempfile.mkdtemp(prefix='babelgg_license_test_')
storage = os.path.join(tmp_dir, 'license.json')

# 1) Fresh install starts as free tier
lm = LicenseManager(storage_path=storage)
assert lm.is_pro() is False, 'Fresh manager should be Free tier'
print('PASS  1 — fresh install is free tier')

# 2) Invalid key path returns error and persists file
_install_fake_requests('invalid')
res = lm.activate('BABELGG-BAD-KEY')
assert res.get('success') is False, 'Invalid key should fail activation'
assert 'Invalid license key' in res.get('message', ''), 'Expected invalid key message'
assert os.path.exists(storage), 'license.json should be created after activation attempt'
print('PASS  2 — invalid key fails and creates storage file')

# 3) Valid key activates Pro and stores metadata
_install_fake_requests('valid')
res = lm.activate('BABELGG-OK-KEY')
assert res.get('success') is True, 'Valid key should activate Pro'
assert lm.is_pro() is True, 'Manager should be Pro after valid activation'
data = lm.get_data()
assert data.get('status') == 'active', 'License status should be active'
assert data.get('instance_id') == 'instance-123', 'Expected instance id from payload'
print('PASS  3 — valid key activates pro and stores metadata')

# 4) Deactivate clears Pro status
ok = lm.deactivate()
assert ok is True, 'Deactivate should return True with mocked API'
assert lm.is_pro() is False, 'Manager should return to Free tier after deactivate'
print('PASS  4 — deactivate clears pro state')

print('\nAll license tests passed')
