from PyInstaller.utils.hooks import collect_all

llama_datas, llama_bins, llama_hidden = collect_all('llama_cpp')
cublas_datas, cublas_bins, cublas_hidden = collect_all('nvidia.cublas')
cuda_runtime_datas, cuda_runtime_bins, cuda_runtime_hidden = collect_all('nvidia.cuda_runtime')
cuda_nvrtc_datas, cuda_nvrtc_bins, cuda_nvrtc_hidden = collect_all('nvidia.cuda_nvrtc')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    runtime_hooks=['rthook_dlls.py'],
    binaries=llama_bins + cublas_bins + cuda_runtime_bins + cuda_nvrtc_bins,
    datas=llama_datas + cublas_datas + cuda_runtime_datas + cuda_nvrtc_datas + [
        ('assets/', 'assets/'),
        ('config.json', '.'),
        ('version.json', '.'),
        ('data/phrases.json', 'data/'),
        ('models/nllb-ct2-cpu/', 'models/nllb-ct2-cpu/'),
    ],
    hiddenimports=llama_hidden + cublas_hidden + cuda_runtime_hidden + cuda_nvrtc_hidden + [
        'llama_cpp', 'huggingface_hub', 'hf_xet',
        'ctranslate2', 'ctranslate2.converters', 'transformers', 'sentencepiece',
        'pyperclip', 'keyboard', 'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore',
        'PyQt6.QtGui', 'GPUtil', 'psutil', 'thefuzz', 'thefuzz.fuzz',
        'core.license', 'core.ocr', 'core.telemetry', 'core.updater',
        'core.emoji_cleaner', 'core.paths', 'ui.downloader', 'ui.ocr_overlay',
        'msvcrt', 'ctypes', 'ctypes.wintypes', 'webbrowser', 'tempfile',
    ],
    excludes=['models', 'tests', 'matplotlib', 'notebook', 'torch', 'torchvision', 'torchaudio', 'torch.distributed', 'torch.utils.tensorboard', 'tensorboard'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

options = [('X utf8', None, 'OPTION')]

exe = EXE(
    pyz,
    a.scripts,
    options,
    exclude_binaries=True,
    name='BabelGG',
    icon='assets/babelgg.ico',
    uac_admin=False,
    console=False,
    strip=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='BabelGG',
)
