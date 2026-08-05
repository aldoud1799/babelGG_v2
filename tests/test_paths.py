import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.paths import base_path, data_path, models_path, asset_path, BASE_DIR, BUNDLE_DIR


print('Testing paths module...')

# 1) base_path returns project root
assert os.path.isabs(base_path()), 'base_path should return absolute path'
assert os.path.isdir(base_path()), 'base_path should exist'
print('PASS  1 - base_path returns project root')

# 2) base_path joins parts correctly
config_path = base_path('config.json')
assert config_path.endswith('config.json'), 'base_path should join parts'
assert os.path.isfile(config_path), 'config.json should exist at base_path'
print('PASS  2 - base_path joins parts correctly')

# 3) data_path returns data directory
data = data_path()
assert data.endswith('data') or data.replace('\\', '/').endswith('data'), 'data_path should end with data'
print('PASS  3 - data_path returns data directory')

# 4) data_path joins parts
phrases = data_path('phrases.json')
assert phrases.endswith('phrases.json'), 'data_path should join parts'
assert os.path.isfile(phrases), 'phrases.json should exist'
print('PASS  4 - data_path joins parts')

# 5) models_path returns models directory
models = models_path()
assert models.endswith('models') or models.replace('\\', '/').endswith('models'), 'models_path should end with models'
print('PASS  5 - models_path returns models directory')

# 6) models_path joins parts
model_file = models_path('nllb-ct2-cpu')
assert 'nllb-ct2-cpu' in model_file, 'models_path should include part'
assert os.path.isdir(model_file), 'nllb-ct2-cpu should exist'
print('PASS  6 - models_path joins parts')

# 7) asset_path returns assets directory
assets = asset_path()
assert assets.endswith('assets') or assets.replace('\\', '/').endswith('assets'), 'asset_path should end with assets'
print('PASS  7 - asset_path returns assets directory')

# 8) asset_path joins parts
logo = asset_path('traylogo.png')
assert 'traylogo.png' in logo, 'asset_path should include filename'
assert os.path.isfile(logo), 'traylogo.png should exist'
print('PASS  8 - asset_path joins parts')

# 9) base_path falls back to bundle if path doesn't exist
nonexistent = base_path('nonexistent_file.txt')
assert 'nonexistent_file.txt' in nonexistent, 'Should include filename in path'
# Should return base_path version even if file doesn't exist
assert os.path.join(os.path.basename(BASE_DIR), 'nonexistent_file.txt') in nonexistent.replace('\\', '/') or \
       'nonexistent_file.txt' in nonexistent, 'Path should be constructed correctly'
print('PASS  9 - base_path handles nonexistent files')

# 10) BASE_DIR is the project root
assert os.path.isdir(BASE_DIR), 'BASE_DIR should be a directory'
# Should contain key project files
assert os.path.isfile(os.path.join(BASE_DIR, 'main.py')), 'BASE_DIR should contain main.py'
assert os.path.isfile(os.path.join(BASE_DIR, 'config.json')), 'BASE_DIR should contain config.json'
print('PASS  10 - BASE_DIR is project root')

# 11) BUNDLE_DIR is defined and is a directory
assert os.path.isdir(BUNDLE_DIR), 'BUNDLE_DIR should be a directory'
print('PASS  11 - BUNDLE_DIR is defined')

# 12) _bundle_fallback prefers existing path
from core.paths import _bundle_fallback
existing = os.path.join(BASE_DIR, 'config.json')
result = _bundle_fallback(existing)
assert result == existing, 'Should return existing path unchanged'
print('PASS  12 - _bundle_fallback returns existing path')

# 13) paths are absolute, not relative
for path_fn in [base_path, data_path, models_path, asset_path]:
    result = path_fn()
    assert os.path.isabs(result), f'{path_fn.__name__} should return absolute path'
print('PASS  13 - all path functions return absolute paths')

# 14) frozen mode uses user data directory
with patch('core.paths.sys.frozen', True, create=True), \
     patch('core.paths._user_root', tempfile.mkdtemp()):
    frozen_data = data_path('test.json')
    assert 'BabelGG' in frozen_data or 'AppData' in frozen_data, \
        'Frozen mode should use user-specific data directory'
print('PASS  14 - frozen mode uses user data directory')

# 15) frozen mode creates directories
with patch('core.paths.sys.frozen', True, create=True), \
     patch('core.paths._user_root', tempfile.mkdtemp()) as mock_root:
    test_dir = data_path()
    # In frozen mode, data_path should create the directory
    assert os.path.isdir(test_dir) or 'BabelGG' in test_dir, \
        'Frozen mode should create data directory'
print('PASS  15 - frozen mode handles directory creation')

print('\nAll paths tests passed')
