import subprocess, sys, os

CORE_TESTS = [
    'tests/test_hardware.py',
    'tests/test_flash.py',
    'tests/test_flash_router.py',
    'tests/test_downloader.py',
    'tests/test_vault.py',
    'tests/test_slang.py',
    'tests/test_emoji_cleaner.py',
    'tests/test_naturalizer.py',
    'tests/test_license.py',
    'tests/test_telemetry.py',
    'tests/test_catch.py',
]

# Keep optional modules in the canonical pass when available in the workspace.
OPTIONAL_CORE_TESTS = [
    'tests/test_paths.py',
    'tests/test_updater.py',
]
CORE_TESTS += [t for t in OPTIONAL_CORE_TESTS if os.path.exists(t)]

EXTENDED_TESTS = [
    'tests/test_all_languages.py',
]

_run_extended = ('--extended' in sys.argv) or (os.environ.get('BABELGG_RUN_EXTENDED_TESTS') == '1')
TESTS = CORE_TESTS + (EXTENDED_TESTS if _run_extended else [])

# Force UTF-8 output in all child processes
_env = os.environ.copy()
_env['PYTHONIOENCODING'] = 'utf-8'
_env['BABELGG_DISABLE_TEST_UNLOCK'] = '1'

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
