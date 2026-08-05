import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.flash import FlashEngine


class FakeFlashEngine(FlashEngine):
    def _resolve_model_path(self) -> str:
        return ''

    def _load(self):
        self.ready = True
        self._profile = ''
        self._llm = object()

    def detect_lang(self, text: str) -> str:
        return 'jpn_Jpan'

    def _ensure_profile(self, profile: str) -> bool:
        self._profile = profile
        self._llm = object()
        return True

    def _deterministic_fallback(self, text: str, tgt: str) -> str:
        return f'FALLBACK:{text}'


class FakeStabilityEngine(FlashEngine):
    def _resolve_model_path(self) -> str:
        return ''

    def _load(self):
        self.ready = True
        self._profile = ''
        self._llm = object()

    def _ensure_profile(self, profile: str) -> bool:
        self._profile = profile
        self._llm = object()
        return True

    def _deterministic_fallback(self, text: str, tgt: str) -> str:
        return text

    def _generate_with_timeout(self, text: str, tgt: str, timeout_ms: int, max_tokens_override=None, strict_target: bool = False):
        # Simulate unchanged model output followed by successful strict retry.
        if strict_target:
            return 'こんにちは、助けが必要です。', False, None
        return text, False, None


# 1) slow streak triggers downgrade
f = FakeFlashEngine(device='cuda')
f._STICKY_PROFILE_RUNTIME = False
f._preferred_profile = 'gpu_full'
f._record_profile_result('gpu_full', 1600, ok=True)
f._record_profile_result('gpu_full', 1520, ok=True)
assert f._preferred_profile == 'gpu_trim', 'Expected downgrade gpu_full -> gpu_trim'
print('PASS  1 — slow streak downgrade works')

# 2) fast streak allows upgrade after cooldown
f._preferred_profile = 'gpu_trim'
f._profile_cooldown_until['gpu_full'] = 0.0
for _ in range(f._FAST_STREAK_TO_RECOVER):
    f._record_profile_result('gpu_trim', 150, ok=True)
assert f._preferred_profile == 'gpu_full', 'Expected upgrade gpu_trim -> gpu_full'
print('PASS  2 — fast streak upgrade works')

# 2b) sticky runtime profile prevents live profile hopping
f_sticky = FakeFlashEngine(device='cuda')
f_sticky._profile = 'gpu_trim'
f_sticky._preferred_profile = 'gpu_full'
profiles = f_sticky._recommended_profiles()
assert profiles == ('gpu_trim', 'cpu_safe', 'fallback'), 'Expected sticky active profile routing with lower-profile fallback'
print('PASS  2b — sticky runtime profile routing works')

# 3) timeout path falls back immediately
f_timeout = FakeFlashEngine(device='cuda')


def _always_timeout(text: str, tgt: str, timeout_ms: int, max_tokens_override=None):
    return '', True, None


f_timeout._generate_with_timeout = _always_timeout
r = f_timeout.translate('未定義テキストXYZ123', 'english')
assert r is not None, 'Expected fallback result dict on timeout'
assert r['profile'] == 'fallback', 'Expected fallback profile on timeout'
assert r['translation'].startswith('FALLBACK:'), 'Expected deterministic fallback translation'
print('PASS  3 — timeout fallback works')

# 4) timeout micro-retry can recover before fallback
f_retry = FakeFlashEngine(device='cuda')
calls = {'n': 0}


def _timeout_then_success(text: str, tgt: str, timeout_ms: int, max_tokens_override=None):
    calls['n'] += 1
    if calls['n'] == 1:
        return '', True, None
    return '<t>Recovered by retry</t>', False, None


f_retry._generate_with_timeout = _timeout_then_success
r = f_retry.translate('長めのテキストでリトライを試します。これはマイクロリトライ回復の検証です。', 'english')
assert r is not None, 'Expected result dict when retry succeeds'
assert r['profile'] != 'fallback', 'Expected non-fallback profile on retry success'
assert 'Recovered by retry' in r['translation'], 'Expected micro-retry translation output'
print('PASS  4 — timeout micro-retry recovery works')

# 5) short ASCII English phrases should stay English (avoid nl misdetect etc.)
f_detect = FakeStabilityEngine(device='cpu')
for phrase in ('i need help', 'help me', 'please help'):
    got = f_detect.detect_lang(phrase)
    assert got == 'eng_Latn', f'Expected eng_Latn for short phrase, got {got} ({phrase})'
print('PASS  5 — short ASCII English detection is stable')

# 6) unchanged non-English output must trigger strict-target recovery
f_stability = FakeStabilityEngine(device='cpu')
r = f_stability.translate('i need help', 'japanese')
assert r is not None, 'Expected translate result for en->ja'
assert r['translation'] != 'i need help', 'Expected unchanged output to be rejected'
assert r['profile'].startswith('strict_retry_'), 'Expected strict retry profile after rejection'
print('PASS  6 — unchanged output rejected and strict retry recovers')

# 7) non-Latin targets require target script signal
assert f_stability._is_target_mismatch_output('i need help', 'jpn_Jpan') is True, 'Expected script mismatch rejection for jpn target'
assert f_stability._is_target_mismatch_output('こんにちは', 'jpn_Jpan') is False, 'Expected Japanese script to pass for jpn target'
print('PASS  7 — non-Latin script acceptance guard works')

print('\nAll flash router tests passed')
