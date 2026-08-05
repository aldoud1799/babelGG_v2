import sys
sys.path.insert(0, '.')

from core.hardware import detect

d = detect()
assert isinstance(d['ram_gb'],  float), 'ram_gb must be float'
assert isinstance(d['vram_gb'], float), 'vram_gb must be float'
assert d['device'] in ('cuda', 'cpu'),  'device must be cuda or cpu'
assert d['gpu'] != '',                  'gpu must not be empty string'
print(f'PASS  hardware: GPU={d["gpu"]}  VRAM={d["vram_gb"]}GB  device={d["device"]}')
