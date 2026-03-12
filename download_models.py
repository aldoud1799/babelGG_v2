"""
BabelGG — First-time model download + conversion.
Run this ONCE before launching BabelGG for the first time.

Requirements:
    pip install huggingface_hub ctranslate2 transformers sentencepiece

Usage:
    python download_models.py
"""
import os, subprocess, sys


def step(msg: str):
    print(f'\n{"="*60}')
    print(f'  {msg}')
    print('='*60)


def main():
    step('Step 1 — Verify ctranslate2 CUDA support')
    try:
        import ctranslate2
        count = ctranslate2.get_cuda_device_count()
        print(f'  ctranslate2 {ctranslate2.__version__}  |  {count} CUDA device(s)')
        if count == 0:
            print('  WARNING: No CUDA devices found — translations will use CPU (3-5s each)')
    except ImportError:
        print('  ERROR: ctranslate2 not installed. Run: pip install ctranslate2')
        sys.exit(1)

    step('Step 2 — Download NLLB-200 distilled 600M (~1.5 GB)')
    if os.path.exists('models/nllb-200-distilled-600M'):
        print('  Already downloaded — skipping')
    else:
        from huggingface_hub import snapshot_download
        path = snapshot_download(
            repo_id='facebook/nllb-200-distilled-600M',
            local_dir='models/nllb-200-distilled-600M',
            ignore_patterns=['*.msgpack', '*.h5', 'flax_*', 'tf_*', 'rust_*'],
        )
        print(f'  Downloaded to: {path}')

    step('Step 3 — Convert to CTranslate2 int8 format')
    if os.path.exists('models/nllb-ct2'):
        print('  Already converted — skipping')
    else:
        # Use full path to the venv converter so it works regardless of PATH
        import sysconfig
        scripts_dir = sysconfig.get_path('scripts')
        converter = os.path.join(scripts_dir, 'ct2-transformers-converter.exe')
        if not os.path.exists(converter):
            converter = 'ct2-transformers-converter'  # fallback to PATH
        result = subprocess.run([
            converter,
            '--model',        'models/nllb-200-distilled-600M',
            '--output_dir',   'models/nllb-ct2',
            '--quantization', 'int8_float16',
            '--force',
        ], check=False)
        if result.returncode != 0:
            print('  ERROR: Conversion failed. Make sure ctranslate2 is installed correctly.')
            sys.exit(1)
        print('  Converted successfully.')

    step('Step 4 — Quick smoke test')
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
