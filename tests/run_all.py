import subprocess, sys, os

TESTS = [
    'tests/test_hardware.py',
    'tests/test_flash.py',
    'tests/test_vault.py',
    'tests/test_slang.py',
    'tests/test_catch.py',
]

# Force UTF-8 output in all child processes
_env = os.environ.copy()
_env['PYTHONIOENCODING'] = 'utf-8'

passed = failed = 0
for test in TESTS:
    r = subprocess.run(
        [sys.executable, test],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        env=_env,
    )
    if r.returncode == 0:
        print(f'PASS  {test}')
        passed += 1
    else:
        print(f'FAIL  {test}')
        print(r.stdout[-600:])
        print(r.stderr[-300:])
        failed += 1

print(f'\n{passed}/{passed + failed} tests passed')
sys.exit(0 if failed == 0 else 1)
