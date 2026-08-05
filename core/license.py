import json
import logging
import os
import time
from datetime import datetime

from core.paths import data_path


PRO_FEATURES = {'natural_mode', 'history', 'presets'}


class LicenseManager:
    # Minimum seconds between online license API calls to avoid rate limiting.
    _ONLINE_VALIDATION_INTERVAL_S = 3600

    def __init__(self, storage_path: str | None = None):
        self._storage_path = storage_path or data_path('license.json')
        self._data = self._load()
        self._pro = False
        self._last_online_validation_ts = 0.0
        self._evaluate()

    def is_pro(self) -> bool:
        return self._pro

    def get_data(self) -> dict:
        return dict(self._data)

    def check(self, feature: str) -> bool:
        if feature not in PRO_FEATURES:
            return True
        return self._pro

    def activate(self, key: str) -> dict:
        key = (key or '').strip()
        if not key:
            return {'success': False, 'message': 'Enter a license key'}

        try:
            import requests

            resp = requests.post(
                'https://api.lemonsqueezy.com/v1/licenses/activate',
                json={'license_key': key, 'instance_name': 'BabelGG'},
                headers={'Accept': 'application/json'},
                timeout=10,
            )
            data = resp.json()
            if resp.status_code == 200 and data.get('activated'):
                now = datetime.utcnow().isoformat()
                license_key_data = data.get('license_key') or {}
                instance_data = data.get('instance') or {}
                plan = (license_key_data.get('product_name') or 'pro').lower()
                if 'lifetime' in plan:
                    plan = 'lifetime'
                elif 'month' in plan:
                    plan = 'monthly'

                self._data = {
                    'key': key,
                    'status': 'active',
                    'plan': plan,
                    'activated_at': now,
                    'last_validated': now,
                    'instance_id': str(instance_data.get('id', '')),
                    'customer_email': str((instance_data.get('meta') or {}).get('customer_email', '')),
                }
                self._save()
                self._pro = True
                logging.info(f'[LICENSE] Activated: {key[:8]}... plan={self._data["plan"]}')
                return {'success': True, 'message': 'Pro activated!', 'plan': self._data['plan']}

            msg = data.get('error') or data.get('message') or 'Invalid license key'
            self._data = {
                'key': key,
                'status': 'inactive',
                'plan': 'free',
                'last_validated': datetime.utcnow().isoformat(),
            }
            self._save()
            self._pro = False
            logging.warning(f'[LICENSE] Activation failed: {msg}')
            return {'success': False, 'message': msg}
        except Exception as e:
            self._data = {
                'key': key,
                'status': 'inactive',
                'plan': 'free',
                'last_validated': datetime.utcnow().isoformat(),
            }
            self._save()
            self._pro = False
            logging.error(f'[LICENSE] activate() failed: {type(e).__name__}: {e}')
            return {'success': False, 'message': 'Connection failed - check internet'}

    def deactivate(self) -> bool:
        if not self._data.get('key'):
            self._data = {}
            self._save()
            self._pro = False
            return True

        try:
            import requests

            requests.post(
                'https://api.lemonsqueezy.com/v1/licenses/deactivate',
                json={
                    'license_key': self._data.get('key', ''),
                    'instance_id': self._data.get('instance_id', ''),
                },
                headers={'Accept': 'application/json'},
                timeout=10,
            )
            self._data = {}
            self._save()
            self._pro = False
            logging.info('[LICENSE] Deactivated')
            return True
        except Exception as e:
            logging.error(f'[LICENSE] deactivate() failed: {type(e).__name__}: {e}')
            return False

    def validate_cached(self):
        if not self._data.get('key'):
            return

        last = self._data.get('last_validated', '')
        if not last:
            try:
                self._validate_online()
            except Exception as e:
                logging.warning(f'[LICENSE] Initial validation failed: {type(e).__name__}: {e}')
            return

        try:
            days_since = (datetime.utcnow() - datetime.fromisoformat(last)).days
        except Exception:
            days_since = 999

        if days_since < 7:
            logging.info('[LICENSE] Validation cached - skipping')
            return

        if days_since < 30:
            try:
                self._validate_online()
            except Exception as e:
                logging.warning(f'[LICENSE] Offline - using grace period ({type(e).__name__})')
                self._data['status'] = 'grace'
                self._save()
                self._pro = True
            return

        logging.warning('[LICENSE] Grace period expired - deactivating')
        self._data['status'] = 'expired'
        self._save()
        self._pro = False

    def _validate_online(self):
        # Rate limit: skip if checked recently
        now = time.time()
        if now - self._last_online_validation_ts < self._ONLINE_VALIDATION_INTERVAL_S:
            logging.info('[LICENSE] Online validation rate-limited — skipping')
            return

        import requests

        resp = requests.post(
            'https://api.lemonsqueezy.com/v1/licenses/validate',
            json={
                'license_key': self._data.get('key', ''),
                'instance_id': self._data.get('instance_id', ''),
            },
            headers={'Accept': 'application/json'},
            timeout=10,
        )
        self._last_online_validation_ts = now
        data = resp.json()
        valid = data.get('valid')
        if valid is None:
            valid = data.get('activated')
        if valid:
            self._data['status'] = 'active'
            self._data['last_validated'] = datetime.utcnow().isoformat()
            self._save()
            self._pro = True
            logging.info('[LICENSE] Online validation passed')
            return

        self._data['status'] = 'inactive'
        self._data['last_validated'] = datetime.utcnow().isoformat()
        self._save()
        self._pro = False
        msg = data.get('error') or data.get('message') or 'invalid'
        logging.warning(f'[LICENSE] Online validation failed: {msg}')

    def _evaluate(self):
        status = self._data.get('status', 'inactive')
        if status in ('active', 'grace'):
            self._pro = True
            logging.info(f'[LICENSE] Pro active - plan={self._data.get("plan", "unknown")}')
        else:
            self._pro = False
            logging.info('[LICENSE] Free tier')

    def _load(self) -> dict:
        try:
            with open(self._storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except FileNotFoundError:
            return {}
        except Exception as e:
            logging.warning(f'[LICENSE] Failed to load license file: {type(e).__name__}: {e}')
        return {}

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            with open(self._storage_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f'[LICENSE] Failed to save license file: {type(e).__name__}: {e}')