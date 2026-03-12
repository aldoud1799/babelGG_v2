block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/',      'assets/'),
        ('config.json',  '.'),
        ('version.json', '.'),
    ],
    hiddenimports=[
        'ctranslate2',
        'transformers',
        'sentencepiece',
        'huggingface_hub',
        'pyperclip',
        'keyboard',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'GPUtil',
        'psutil',
        'thefuzz',
        'thefuzz.fuzz',
    ],
    excludes=[
        'models',     # models are NOT bundled — too large
        'tests',
        'matplotlib',
        'notebook',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BabelGG',
    icon='assets/icon.ico',
    uac_admin=True,
    console=False,
    onefile=True,
    strip=False,
    upx=True,
)
