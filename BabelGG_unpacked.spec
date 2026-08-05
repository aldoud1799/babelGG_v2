block_cipher = None

from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/',            'assets/'),
        ('config.json',        '.'),
        ('version.json',       '.'),
        ('data/phrases.json',  'data/'),
        ('data/meta.json',     'data/'),
        ('data/cuda/',         'data/cuda/'),
        ('data/cuda/bin/cublas64_12.dll', 'ctranslate2/'),
        ('.venv311/Lib/site-packages/nvidia/cublas/bin/cublasLt64_12.dll', 'nvidia/cublas/bin/'),
        ('.venv311/Lib/site-packages/nvidia/cublas/bin/cublasLt64_12.dll', 'ctranslate2/'),
        ('.venv311/Lib/site-packages/nvidia/cuda_runtime/bin/cudart64_12.dll', 'ctranslate2/'),
        ('models/small100-ct2/', 'models/small100-ct2/'),
        ('models/nllb-200-distilled-600M/', 'models/nllb-200-distilled-600M/'),
    ] + collect_data_files('ctranslate2'),
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.sip',
        'ctranslate2',
        'sentencepiece',
        'huggingface_hub',
        'huggingface_hub.utils',
        'pyperclip',
        'keyboard',
        'GPUtil',
        'psutil',
        'psutil._pswindows',
        'thefuzz',
        'thefuzz.fuzz',
        'thefuzz.process',
        'rapidfuzz',
        'requests',
        'urllib3',
        'charset_normalizer',
        'certifi',
        'pkg_resources',
    ],
    runtime_hooks=['hook_notorch.py'],
    excludes=[
        'torch',
        'torch.nn',
        'torch.cuda',
        'torchvision',
        'torchaudio',
        'tensorflow',
        'tensorflow_core',
        'keras',
        'matplotlib',
        'notebook',
        'IPython',
        'scipy',
        'pandas',
        'tkinter',
        'unittest',
        'test',
        'pip',
    ],
    noarchive=False,
)

# Avoid bundling PyQt's MSVCP140 copies, which can crash at runtime on some systems.
def _drop_qt_msvc(entry):
    dst = (entry[0] or '').replace('/', '\\').lower().lstrip('\\')
    src = (entry[1] or '').replace('/', '\\').lower().lstrip('\\')
    in_qt_bin = ('pyqt6\\qt6\\bin\\' in dst) or ('pyqt6\\qt6\\bin\\' in src)
    if not in_qt_bin:
        return False
    bad = ('msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll')
    return any(dst.endswith('\\' + n) or dst == n or src.endswith('\\' + n) or src == n for n in bad)


a.binaries = [entry for entry in a.binaries if not _drop_qt_msvc(entry)]
a.datas = [entry for entry in a.datas if not _drop_qt_msvc(entry)]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
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
