import os, shutil, pathlib

dist = pathlib.Path('dist/BabelGG')

# Remove conflicting PyQt6 runtime DLLs that crash ctranslate2
for dll in ['MSVCP140.dll', 'VCRUNTIME140.dll', 'VCRUNTIME140_1.dll']:
    p = dist / '_internal' / 'PyQt6' / 'Qt6' / 'bin' / dll
    if p.exists():
        p.unlink()
        print(f'Removed: {p}')

# Copy CUDA DLLs
nvidia = pathlib.Path('.venv311/Lib/site-packages/nvidia')
internal = dist / '_internal'

for dll in (nvidia / 'cublas/bin').glob('*64_12.dll'):
    shutil.copy2(dll, internal)
    print(f'Copied: {dll.name}')

shutil.copy2(nvidia / 'cuda_runtime/bin/cudart64_12.dll', internal)
print('Copied: cudart64_12.dll')

for dll in (nvidia / 'cudnn/bin').glob('*.dll'):
    shutil.copy2(dll, internal)
    print(f'Copied: {dll.name}')

# data/cuda/bin
cuda_bin = dist / 'data' / 'cuda' / 'bin'
cuda_bin.mkdir(parents=True, exist_ok=True)
shutil.copy2('data/cuda/bin/cublas64_12.dll', cuda_bin)
print('Copied: data/cuda/bin/cublas64_12.dll')

print('Post-build complete.')
