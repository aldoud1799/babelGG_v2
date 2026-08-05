"""
BabelGG — First-time model download for NLLB-200 CTranslate2 models.
Run this once before launching BabelGG for the first time.

Requirements:
    pip install huggingface_hub ctranslate2 transformers

Usage:
    python download_models.py
"""
import os, sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def app_path(*parts: str) -> str:
    return os.path.join(BASE_DIR, *parts)


def step(msg: str):
    print(f'\n{"="*60}')
    print(f'  {msg}')
    print('='*60)


def main():
    step('Step 1 — Verify CTranslate2 installation')
    try:
        import ctranslate2
        print(f'  CTranslate2 installed')
    except ImportError:
        print('  ERROR: ctranslate2 not installed. Run: pip install ctranslate2 transformers')
        sys.exit(1)

    step('Step 2 — Verify NLLB CT2 models')
    cpu_dir = app_path('models', 'nllb-ct2-cpu')
    gpu_dir = app_path('models', 'nllb-ct2-gpu')
    
    if os.path.isdir(cpu_dir) and os.path.isdir(gpu_dir):
        print('  Models already present — skipping')
    else:
        print('  Please run model conversion script or download from HuggingFace')
        print('  CPU model:', cpu_dir)
        print('  GPU model:', gpu_dir)
        print('  Models not found. See build.md for conversion instructions.')

    step('Step 3 — Quick smoke test')
    from core.flash import FlashEngine
    import logging
    logging.basicConfig(level=logging.WARNING)
    f = FlashEngine()
    if f.ready:
        r = f.translate('今日一緒にゲームしよう！', 'english')
        if r:
            print(f'  Translation OK: {r["translation"]}  ({r["ms"]}ms)')
        else:
            print('  WARNING: translate() returned None')
    else:
        print('  ERROR: FlashEngine not ready — check logs above')
        sys.exit(1)

    print('\n✓ Setup complete! Run: python main.py')


if __name__ == '__main__':
    main()
