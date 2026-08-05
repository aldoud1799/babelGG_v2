import os, sys

# Add _internal nvidia DLL paths to Windows DLL search path
if hasattr(sys, '_MEIPASS'):
    base = sys._MEIPASS
    dll_dirs = [
        base,
        os.path.join(base, 'torch', 'lib'),
        os.path.join(base, 'ctranslate2'),
    ]
    for d in dll_dirs:
        if os.path.isdir(d):
            os.add_dll_directory(d)
