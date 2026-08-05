import os, sys
if hasattr(sys, '_MEIPASS'):
    base = sys._MEIPASS
    for sub in ['', 'nvidia/cublas/bin', 'nvidia/cuda_nvrtc/bin', 'nvidia/cuda_runtime/bin', 'data/cuda/bin']:
        d = os.path.join(base, sub)
        if os.path.isdir(d):
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
