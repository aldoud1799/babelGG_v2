import os
import sys


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    _user_root = os.path.join(os.environ.get('LOCALAPPDATA', BASE_DIR), 'BabelGG')
    _meipass = getattr(sys, '_MEIPASS', '')
    _internal_dir = os.path.join(BASE_DIR, '_internal')
    if _meipass and os.path.isdir(_meipass):
        BUNDLE_DIR = _meipass
    elif os.path.isdir(_internal_dir):
        BUNDLE_DIR = _internal_dir
    else:
        BUNDLE_DIR = BASE_DIR
else:
    # core/paths.py lives under core/, so project root is one level up.
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _user_root = BASE_DIR
    BUNDLE_DIR = BASE_DIR


def _bundle_fallback(path: str) -> str:
    if os.path.exists(path):
        return path
    rel = os.path.relpath(path, BASE_DIR)
    fallback = os.path.join(BUNDLE_DIR, rel)
    if os.path.exists(fallback):
        return fallback
    return path


def base_path(*parts: str) -> str:
    return _bundle_fallback(os.path.join(BASE_DIR, *parts))


def data_path(*parts: str) -> str:
    if getattr(sys, 'frozen', False):
        root = os.path.join(_user_root, 'data')
        os.makedirs(root, exist_ok=True)
        return os.path.join(root, *parts)
    return _bundle_fallback(os.path.join(BASE_DIR, 'data', *parts))


def user_config_path() -> str:
    """Return path to user's writable config.json."""
    if getattr(sys, 'frozen', False):
        return os.path.join(_user_root, 'config.json')
    return os.path.join(BASE_DIR, 'config.json')


def models_path(*parts: str) -> str:
    if getattr(sys, 'frozen', False):
        root = os.path.join(_user_root, 'models')
        os.makedirs(root, exist_ok=True)
        return os.path.join(root, *parts)
    return _bundle_fallback(os.path.join(BASE_DIR, 'models', *parts))


def asset_path(*parts: str) -> str:
    return _bundle_fallback(os.path.join(BASE_DIR, 'assets', *parts))
