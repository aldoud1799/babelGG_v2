import ctypes
import logging
import os
import platform
import subprocess
import sys

import psutil

try:
    import GPUtil
    _HAS_GPUTIL = True
except ImportError:
    _HAS_GPUTIL = False


def _add_windows_cuda_dirs() -> list[str]:
    """Best-effort DLL directory bootstrap for CUDA runtime discovery on Windows."""
    if os.name != 'nt' or not hasattr(os, 'add_dll_directory'):
        return []

    roots = []
    for key, value in os.environ.items():
        if key.startswith('CUDA_PATH') and value:
            roots.append(value)

    if os.environ.get('ProgramFiles'):
        toolkit_root = os.path.join(os.environ['ProgramFiles'], 'NVIDIA GPU Computing Toolkit', 'CUDA')
        if os.path.isdir(toolkit_root):
            for entry in sorted(os.listdir(toolkit_root), reverse=True):
                roots.append(os.path.join(toolkit_root, entry))

    exe_dir = os.path.dirname(sys.executable)
    roots.extend([
        exe_dir,
        os.path.join(exe_dir, '_internal'),
        os.path.join(exe_dir, '_internal', 'nvidia', 'cublas', 'bin'),
        os.path.join(exe_dir, '_internal', 'nvidia', 'cuda_nvrtc', 'bin'),
        os.path.join(exe_dir, '_internal', 'nvidia', 'cuda_runtime', 'bin'),
        os.path.join(exe_dir, 'data', 'cuda', 'bin'),
    ])

    # Also support CUDA runtime DLLs from pip wheels (nvidia-* -cu12).
    for p in sys.path:
        if not p:
            continue
        roots.extend([
            os.path.join(p, 'nvidia', 'cublas', 'bin'),
            os.path.join(p, 'nvidia', 'cuda_nvrtc', 'bin'),
            os.path.join(p, 'nvidia', 'cuda_runtime', 'bin'),
        ])

    added = []
    seen = set()
    for root in roots:
        if not root:
            continue
        bin_dir = os.path.join(root, 'bin') if not root.lower().endswith('bin') else root
        norm = os.path.normcase(os.path.normpath(bin_dir))
        if norm in seen or not os.path.isdir(bin_dir):
            continue
        seen.add(norm)
        try:
            os.add_dll_directory(bin_dir)
            added.append(bin_dir)
        except Exception:
            continue
    return added


def _ct2_cuda_available() -> tuple[bool, str]:
    """Return whether CTranslate2 can use CUDA in this process."""
    if os.name == 'nt':
        _add_windows_cuda_dirs()
        required = ('cublas64_12.dll', 'cublasLt64_12.dll', 'cudart64_12.dll')
        for dll_name in required:
            try:
                ctypes.WinDLL(dll_name)
            except Exception as e:
                return (False, f'Missing CUDA runtime DLL {dll_name}: {e}')

    try:
        import ctranslate2
    except Exception as e:
        return (False, f'ctranslate2 import failed: {type(e).__name__}: {e}')

    try:
        count = int(ctranslate2.get_cuda_device_count())
    except Exception as e:
        return (False, f'ctranslate2 CUDA probe failed: {type(e).__name__}: {e}')

    if count <= 0:
        return (False, 'No CUDA-capable devices available to ctranslate2')
    return (True, f'CUDA devices detected: {count}')


def _detect_avx_flags() -> tuple[bool, bool]:
    """Return (avx2, avx512f), preferring CPUID on Windows for reliability."""
    if os.name == 'nt':
        try:
            return _detect_avx_flags_windows_cpuid()
        except Exception as e:
            logging.warning(f'[HARDWARE] CPUID AVX detect failed: {type(e).__name__}: {e}')
            # Best-effort fallback visibility only (does not determine AVX flags).
            try:
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'Caption', '/value'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                caption = (result.stdout or '').strip().replace('\n', ' | ')
                if caption:
                    logging.info(f'[HARDWARE] WMIC CPU caption: {caption}')
            except Exception:
                pass

    # Non-Windows (or Windows fallback): try cpuinfo.
    try:
        import cpuinfo  # optional dependency

        flags = cpuinfo.get_cpu_info().get('flags', [])
        return ('avx2' in flags, 'avx512f' in flags)
    except Exception:
        return (False, False)


def _detect_avx_flags_windows_cpuid() -> tuple[bool, bool]:
    """CPUID-based AVX flag detection for Windows x64 Python processes."""
    if platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError(f'Unsupported machine for CPUID probe: {platform.machine()}')

    kernel32 = ctypes.windll.kernel32
    kernel32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong, ctypes.c_ulong]
    kernel32.VirtualAlloc.restype = ctypes.c_void_p
    kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_ulong]
    kernel32.VirtualFree.restype = ctypes.c_int
    MEM_COMMIT = 0x1000
    MEM_RESERVE = 0x2000
    PAGE_EXECUTE_READWRITE = 0x40

    # x64 assembly:
    # mov eax, ecx
    # mov ecx, edx
    # cpuid
    # mov r10, r8
    # mov [r10], eax
    # mov [r10+4], ebx
    # mov [r10+8], ecx
    # mov [r10+12], edx
    # ret
    code = bytes([
        0x89, 0xC8,
        0x89, 0xD1,
        0x0F, 0xA2,
        0x4D, 0x89, 0xC2,
        0x41, 0x89, 0x02,
        0x41, 0x89, 0x5A, 0x04,
        0x41, 0x89, 0x4A, 0x08,
        0x41, 0x89, 0x52, 0x0C,
        0xC3,
    ])

    size = len(code)
    ptr = kernel32.VirtualAlloc(None, size, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE)
    if not ptr:
        raise RuntimeError('VirtualAlloc failed for CPUID probe')

    try:
        ctypes.memmove(ctypes.c_void_p(ptr), code, size)
        CPUIDFUNC = ctypes.CFUNCTYPE(None, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))
        cpuid_fn = CPUIDFUNC(ptr)

        out = (ctypes.c_uint32 * 4)()
        cpuid_fn(0, 0, out)
        max_basic_leaf = int(out[0])

        avx2 = False
        avx512f = False
        if max_basic_leaf >= 7:
            cpuid_fn(7, 0, out)
            ebx = int(out[1])
            avx2 = bool((ebx >> 5) & 1)
            avx512f = bool((ebx >> 16) & 1)
        return (avx2, avx512f)
    finally:
        kernel32.VirtualFree(ctypes.c_void_p(ptr), 0, 0x8000)


def detect() -> dict:
    ram_gb   = round(psutil.virtual_memory().total / 1e9, 1)
    cpu_cores = psutil.cpu_count(logical=False) or 2
    cpu_threads = psutil.cpu_count(logical=True) or max(cpu_cores, 2)
    gpu_name = 'None'
    vram_gb  = 0.0

    avx2, avx512 = _detect_avx_flags()

    if _HAS_GPUTIL:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_name = gpus[0].name
                vram_gb  = round(gpus[0].memoryTotal / 1024, 1)
        except Exception as e:
            logging.warning(f'[HARDWARE] GPU detect failed: {e}')

    # Probe CT2 CUDA availability directly; GPUtil visibility can be incomplete
    # on some machines while CUDA runtime itself is healthy.
    cuda_ok, cuda_reason = _ct2_cuda_available()

    device = 'cuda' if cuda_ok else 'cpu'
    info = {
        'ram_gb':  ram_gb,
        'gpu':     gpu_name,
        'vram_gb': vram_gb,
        'device':  device,
        'cuda_available': cuda_ok,
        'cuda_reason': cuda_reason,
        'cpu_cores': cpu_cores,
        'cpu_threads': cpu_threads,
        'optimal_threads': max(2, cpu_cores),
        'avx2': avx2,
        'avx512': avx512,
    }
    logging.info(
        f'[HARDWARE] RAM={ram_gb}GB GPU={gpu_name} VRAM={vram_gb}GB '
        f'device={device} cores={cpu_cores} threads={cpu_threads} '
        f'AVX2={avx2} AVX512={avx512} optimal_threads={max(2, cpu_cores)} '
        f'CUDA_OK={cuda_ok} CUDA_REASON={cuda_reason}'
    )
    return info


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    d = detect()
    print(f'   GPU:     {d["gpu"]}')
    print(f'   VRAM:    {d["vram_gb"]} GB')
    print(f'   RAM:     {d["ram_gb"]} GB')
    print(f'   Cores:   {d["cpu_cores"]}')
    print(f'   Threads: {d["cpu_threads"]}')
    print(f'   AVX2:    {d["avx2"]}')
    print(f'   AVX512:  {d["avx512"]}')
    print(f'   Device:  {d["device"]}')
