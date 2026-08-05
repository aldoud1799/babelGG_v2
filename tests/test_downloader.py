import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ui.downloader import _resolve_config_path, _gguf_is_valid, _friendly_download_error, needs_download


# 1) path resolver keeps absolute path
abs_in = os.path.abspath(os.path.join('models', 'abc.gguf'))
assert _resolve_config_path(abs_in) == abs_in, 'Absolute path should be returned unchanged'
print('PASS  1 - absolute path resolution')

# 2) path resolver maps models/* to workspace models path
p = _resolve_config_path('models/nllb-ct2-cpu')
assert p.replace('\\', '/').endswith('/models/nllb-ct2-cpu'), 'models path should resolve into workspace models dir'
print('PASS  2 - models relative path resolution')

# 3) gguf validator checks both file existence and minimum size threshold
with patch('ui.downloader.os.path.isfile', return_value=True), patch('ui.downloader.os.path.getsize', return_value=(301 * 1024 * 1024)):
    assert _gguf_is_valid('x.gguf') is True, 'Expected valid when size is above threshold'
with patch('ui.downloader.os.path.isfile', return_value=True), patch('ui.downloader.os.path.getsize', return_value=(150 * 1024 * 1024)):
    assert _gguf_is_valid('x.gguf') is False, 'Expected invalid when size is below threshold'
print('PASS  3 - gguf size validation')

# 4) user-facing error mapping is actionable for common failure classes
msg = _friendly_download_error(RuntimeError('Connection timed out while fetching metadata'))
assert 'timeout' in msg.lower(), 'Expected timeout-specific message'
msg = _friendly_download_error(RuntimeError('403 Client Error: Forbidden'))
assert 'denied' in msg.lower(), 'Expected auth/permission-specific message'
print('PASS  4 - error message mapping')

# 5) needs_download returns False when CPU CT2 model is complete
cfg = {
    'flash': {
        'local_ct2_gpu_path': 'models/nllb-ct2-gpu',
        'local_ct2_cpu_path': 'models/nllb-ct2-cpu',
    }
}
with patch('ui.downloader.os.path.isfile') as _isfile:
    def _fake_isfile(path: str) -> bool:
        return path.replace('\\', '/').endswith('/models/nllb-ct2-cpu/model.bin')
    _isfile.side_effect = _fake_isfile
    assert needs_download(cfg) is False, 'Expected no download when CPU model.bin exists'
print('PASS  5 - needs_download skips when CPU model is ready')

# 6) needs_download returns True when neither GPU nor CPU CT2 model is complete
with patch('ui.downloader.os.path.isfile', return_value=False):
    assert needs_download(cfg) is True, 'Expected download required when no CT2 model.bin exists'
print('PASS  6 - needs_download requires setup when models are missing')

# 7) needs_download recognizes bundled GPU model path via base_path fallback
with patch('ui.downloader.base_path', return_value='C:/bundle/models/nllb-ct2-gpu'), \
     patch('ui.downloader.models_path', return_value='C:/users/local/models/nllb-ct2-gpu'), \
     patch('ui.downloader.os.path.isfile') as _isfile:
    def _fake_isfile_bundle(path: str) -> bool:
        p = path.replace('\\', '/')
        return p.endswith('/bundle/models/nllb-ct2-gpu/model.bin')
    _isfile.side_effect = _fake_isfile_bundle
    assert needs_download(cfg, required_device='cuda') is False, 'Expected no download when bundled GPU model exists'
print('PASS  7 - bundled GPU model is accepted')

# 8) CUDA device request requires a GPU CT2 model to preserve acceleration
with patch('ui.downloader.base_path', side_effect=lambda *parts: 'C:/bundle/' + '/'.join(parts)), \
     patch('ui.downloader.models_path', side_effect=lambda *parts: 'C:/users/local/' + '/'.join(parts)), \
     patch('ui.downloader.os.path.isfile') as _isfile:
    def _fake_isfile_cpu_only(path: str) -> bool:
        p = path.replace('\\', '/')
        return p.endswith('/bundle/models/nllb-ct2-cpu/model.bin')
    _isfile.side_effect = _fake_isfile_cpu_only
    assert needs_download(cfg, required_device='cuda') is True, 'Expected download when CUDA model is missing'
print('PASS  8 - CUDA request requires GPU model readiness')

print('\nAll downloader tests passed')
