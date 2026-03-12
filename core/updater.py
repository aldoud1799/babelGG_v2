"""
core/updater.py — Silent background update checker.

Spawned as a daemon thread after FLASH is ready.
- Fetches version.json from GitHub once per day
- Compares app_version / minimum_version against the running version
- Fires a tray notification if an update is available
- Never blocks, never crashes on network/parse errors
"""
import json, logging, os, threading, time
from urllib.request import urlopen, Request
from urllib.error   import URLError
from packaging.version import Version
from core.paths import data_path

# Raw URL for version.json in the canonical repo branch
VERSION_URL    = 'https://raw.githubusercontent.com/aldoud1799/babelGG_v2/main/version.json'
RELEASES_URL   = 'https://github.com/aldoud1799/babelGG_v2/releases'
META_PATH      = data_path('meta.json')
CHECK_INTERVAL = 86400          # 24 hours in seconds
FETCH_TIMEOUT  = 8              # seconds


def _load_meta() -> dict:
    try:
        with open(META_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_meta(meta: dict):
    os.makedirs(data_path(), exist_ok=True)
    try:
        with open(META_PATH, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)
    except Exception as e:
        logging.warning(f'[UPDATER] Could not save meta.json: {e}')


def _fetch_remote_version() -> dict | None:
    """Return parsed remote version.json, or None on any failure."""
    try:
        req = Request(VERSION_URL, headers={'User-Agent': 'BabelGG-updater/1'})
        with urlopen(req, timeout=FETCH_TIMEOUT) as resp:
            raw = resp.read().decode('utf-8')
        return json.loads(raw)
    except (URLError, OSError) as e:
        logging.info(f'[UPDATER] Network unavailable: {e}')
        return None
    except (json.JSONDecodeError, ValueError) as e:
        logging.warning(f'[UPDATER] Bad remote version.json: {e}')
        return None
    except Exception as e:
        logging.warning(f'[UPDATER] Unexpected fetch error: {e}')
        return None


def _should_check(meta: dict) -> bool:
    last = meta.get('last_update_check', 0)
    return (time.time() - last) >= CHECK_INTERVAL


def _check(running_ver: str, tray) -> None:
    """Core check logic — always safe to call, never raises."""
    try:
        meta = _load_meta()
        if not _should_check(meta):
            logging.info('[UPDATER] Skipping check — checked less than 24h ago')
            return

        logging.info(f'[UPDATER] Checking for updates (running {running_ver})...')
        remote = _fetch_remote_version()
        if remote is None:
            return

        meta['last_update_check'] = time.time()
        _save_meta(meta)

        remote_ver  = remote.get('app_version', '0.0.0')
        min_ver     = remote.get('minimum_version', '0.0.0')

        running = Version(running_ver)
        latest  = Version(remote_ver)
        minimum = Version(min_ver)

        if running < minimum:
            # Critical: this version is no longer supported
            msg = (
                f'BabelGG {running_ver} is no longer supported — '
                f'please update to {remote_ver}'
            )
            logging.warning(f'[UPDATER] {msg}')
            _show_notification(tray, '⚠ Unsupported Version', msg, critical=True)
        elif latest > running:
            msg = f'BabelGG {remote_ver} is available — click to download'
            logging.info(f'[UPDATER] Update available: {remote_ver}')
            _show_notification(tray, 'Update Available', msg, critical=False)
        else:
            logging.info(f'[UPDATER] Up to date ({running_ver})')

    except Exception as e:
        logging.warning(f'[UPDATER] Check failed unexpectedly: {e}')


def _show_notification(tray, title: str, message: str, critical: bool) -> None:
    """
    Emit tray balloon via signal (thread-safe — Qt queues onto main thread).
    Wires a one-shot click handler to open the releases page in the browser.
    """
    from PyQt6.QtWidgets import QSystemTrayIcon
    import webbrowser

    icon = (QSystemTrayIcon.MessageIcon.Critical if critical
            else QSystemTrayIcon.MessageIcon.Information)

    # One-shot: open browser when the user clicks the balloon
    def _on_click():
        webbrowser.open(RELEASES_URL)
        try:
            tray.messageClicked.disconnect(_on_click)
        except Exception:
            pass

    tray.messageClicked.connect(_on_click)

    # notify_requested is connected with AutoConnection — safe from any thread
    tray.notify_requested.emit(title, message, icon.value)


# ── Public API ────────────────────────────────────────────────────────────────

def start(running_ver: str, tray) -> None:
    """
    Spawn a daemon thread that checks for updates once.
    Safe to call immediately after FLASH is ready — will not block.
    """
    t = threading.Thread(
        target=_check,
        args=(running_ver, tray),
        daemon=True,
        name='UpdateCheck',
    )
    t.start()
    logging.info('[UPDATER] Check thread started')
