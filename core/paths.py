import os
import sys


if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # core/paths.py lives under core/, so project root is one level up.
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def base_path(*parts: str) -> str:
    return os.path.join(BASE_DIR, *parts)


def data_path(*parts: str) -> str:
    return os.path.join(BASE_DIR, 'data', *parts)


def models_path(*parts: str) -> str:
    return os.path.join(BASE_DIR, 'models', *parts)


def asset_path(*parts: str) -> str:
    return os.path.join(BASE_DIR, 'assets', *parts)
