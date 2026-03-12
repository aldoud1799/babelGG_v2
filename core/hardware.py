import psutil, logging

try:
    import GPUtil
    _HAS_GPUTIL = True
except ImportError:
    _HAS_GPUTIL = False


def detect() -> dict:
    ram_gb   = round(psutil.virtual_memory().total / 1e9, 1)
    gpu_name = 'None'
    vram_gb  = 0.0

    if _HAS_GPUTIL:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_name = gpus[0].name
                vram_gb  = round(gpus[0].memoryTotal / 1024, 1)
        except Exception as e:
            logging.warning(f'[HARDWARE] GPU detect failed: {e}')

    device = 'cuda' if vram_gb >= 2.0 else 'cpu'
    info = {
        'ram_gb':  ram_gb,
        'gpu':     gpu_name,
        'vram_gb': vram_gb,
        'device':  device,
    }
    logging.info(
        f'[HARDWARE] RAM={ram_gb}GB  GPU={gpu_name}  VRAM={vram_gb}GB  device={device}'
    )
    return info


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    d = detect()
    print(f'   GPU:     {d["gpu"]}')
    print(f'   VRAM:    {d["vram_gb"]} GB')
    print(f'   RAM:     {d["ram_gb"]} GB')
    print(f'   Device:  {d["device"]}')
