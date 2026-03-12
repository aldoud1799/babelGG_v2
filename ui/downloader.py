"""
ui/downloader.py — First-run model download dialog.

Shows before FlashEngine is warmed. Downloads NLLB-200 from HuggingFace
then converts it to CTranslate2 int8 format. Runs entirely in a background
thread so the progress bar stays live and Cancel works immediately.
"""
import json, logging, os, shutil, subprocess, sysconfig, threading

from PyQt6.QtCore    import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QSizePolicy,
)
from PyQt6.QtGui import QFont


# ── Worker ────────────────────────────────────────────────────────────────────

class _DownloadWorker(QObject):
    """Runs in a QThread.  Emits progress / status / finished / error."""

    progress  = pyqtSignal(int)          # 0-100
    status    = pyqtSignal(str)          # status-bar text
    finished  = pyqtSignal()
    error     = pyqtSignal(str)

    def __init__(self, hf_repo: str, hf_path: str, ct2_path: str, quantization: str):
        super().__init__()
        self._hf_repo      = hf_repo
        self._hf_path      = hf_path
        self._ct2_path     = ct2_path
        self._quantization = quantization
        self._cancel       = threading.Event()

    def cancel(self):
        self._cancel.set()

    # ── main work ──────────────────────────────────────────────────────────
    def run(self):
        try:
            self._download_hf()
            if self._cancel.is_set():
                return
            self._convert_ct2()
            if self._cancel.is_set():
                return
            self.finished.emit()
        except Exception as exc:
            if not self._cancel.is_set():
                logging.error(f'[DOWNLOADER] {exc}')
                self.error.emit(str(exc))

    # ── Step 1: HuggingFace snapshot download ──────────────────────────────
    def _download_hf(self):
        if os.path.isdir(self._hf_path) and os.listdir(self._hf_path):
            logging.info('[DOWNLOADER] HF model already present, skipping download')
            self.progress.emit(50)
            return

        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import tqdm as hf_tqdm

        # We monkey-patch tqdm so we get byte-level progress without extra deps.
        # huggingface_hub uses tqdm internally for each file; we track the total
        # via a simple accumulator updated on each tqdm update call.
        _total_bytes   = [0]
        _done_bytes    = [0]
        _orig_tqdm     = hf_tqdm.__init__          # keep original

        worker_self    = self  # capture for closure

        def _patched_init(tqdm_self, *args, **kwargs):
            _orig_tqdm(tqdm_self, *args, **kwargs)
            total = getattr(tqdm_self, 'total', None)
            if total:
                _total_bytes[0] += total

        _orig_update   = hf_tqdm.update

        def _patched_update(tqdm_self, n=1):
            _orig_update(tqdm_self, n)
            _done_bytes[0] += n
            if _total_bytes[0] > 0:
                pct = min(49, int(_done_bytes[0] / _total_bytes[0] * 49))
                worker_self.progress.emit(pct)
            done_mb  = _done_bytes[0] / (1024 * 1024)
            total_mb = _total_bytes[0] / (1024 * 1024)
            if total_mb > 0:
                worker_self.status.emit(
                    f'Downloading... {done_mb:.0f} MB / {total_mb:.0f} MB'
                )
            if worker_self._cancel.is_set():
                tqdm_self.close()

        hf_tqdm.__init__ = _patched_init
        hf_tqdm.update   = _patched_update

        try:
            self.status.emit('Connecting to HuggingFace...')
            snapshot_download(
                repo_id        = self._hf_repo,
                local_dir      = self._hf_path,
                ignore_patterns= ['*.msgpack', '*.h5', 'flax_*', 'tf_*', 'rust_*'],
            )
        finally:
            # Always restore originals
            hf_tqdm.__init__ = _orig_tqdm
            hf_tqdm.update   = _orig_update

        if self._cancel.is_set():
            return
        self.progress.emit(50)
        self.status.emit('Download complete.')

    # ── Step 2: CTranslate2 conversion ─────────────────────────────────────
    def _convert_ct2(self):
        if os.path.isdir(self._ct2_path) and os.listdir(self._ct2_path):
            logging.info('[DOWNLOADER] CT2 model already present, skipping conversion')
            self.progress.emit(100)
            return

        self.status.emit('Converting model to fast format (this takes ~1 min)...')
        self.progress.emit(55)

        scripts_dir = sysconfig.get_path('scripts')
        converter   = os.path.join(scripts_dir, 'ct2-transformers-converter.exe')
        if not os.path.exists(converter):
            converter = os.path.join(scripts_dir, 'ct2-transformers-converter')
        if not os.path.exists(converter):
            converter = 'ct2-transformers-converter'   # last resort: PATH

        cmd = [
            converter,
            '--model',        self._hf_path,
            '--output_dir',   self._ct2_path,
            '--quantization', self._quantization,
            '--force',
        ]
        logging.info(f'[DOWNLOADER] Running: {" ".join(cmd)}')

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
        )

        # Drain output; bump progress bar from 55 → 95 linearly while running
        line_count = 0
        for line in proc.stdout:
            if self._cancel.is_set():
                proc.kill()
                return
            line_count += 1
            pct = min(95, 55 + line_count)
            self.progress.emit(pct)
            logging.debug(f'[CT2] {line.rstrip()}')

        proc.wait()
        if proc.returncode != 0 and not self._cancel.is_set():
            raise RuntimeError(
                f'ct2-transformers-converter exited with code {proc.returncode}. '
                'Check data/babelgg.log for details.'
            )

        self.progress.emit(100)
        self.status.emit('Conversion complete.')


# ── Dialog ────────────────────────────────────────────────────────────────────

class DownloaderDialog(QDialog):
    """
    Shown once on first run or when models/nllb-ct2/ is missing.
    Blocks BabelGG.start() until download + conversion succeed
    (or the user cancels, which quits the app).

    Usage:
        dlg = DownloaderDialog(version_cfg, parent=None)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)       # user cancelled
    """

    STYLE = """
        QDialog {
            background: #1A1A2E;
        }
        QLabel#title {
            color: #FFFFFF;
            font-size: 16px;
            font-weight: bold;
        }
        QLabel#subtitle {
            color: #A0A0B0;
            font-size: 12px;
        }
        QLabel#status {
            color: #00C2A8;
            font-size: 12px;
        }
        QProgressBar {
            background: #2A2A4E;
            border: 1px solid #3A3A5E;
            border-radius: 4px;
            height: 18px;
            text-align: center;
            color: #FFFFFF;
            font-size: 11px;
        }
        QProgressBar::chunk {
            background: #00C2A8;
            border-radius: 3px;
        }
        QPushButton#cancel {
            background: #2A2A4E;
            color: #A0A0B0;
            border: 1px solid #3A3A5E;
            border-radius: 4px;
            padding: 6px 20px;
            font-size: 12px;
        }
        QPushButton#cancel:hover {
            background: #3A2A4E;
            color: #FFFFFF;
        }
        QPushButton#retry {
            background: #00C2A8;
            color: #000000;
            border: none;
            border-radius: 4px;
            padding: 6px 20px;
            font-size: 12px;
            font-weight: bold;
        }
        QPushButton#retry:hover {
            background: #00E0C0;
        }
    """

    def __init__(self, version_cfg: dict, parent=None):
        super().__init__(parent)
        flash           = version_cfg.get('flash', {})
        self._hf_repo   = flash.get('repo',         'facebook/nllb-200-distilled-600M')
        self._hf_path   = flash.get('local_hf_path','models/nllb-200-distilled-600M')
        self._ct2_path  = flash.get('local_ct2_path','models/nllb-ct2')
        self._quant     = flash.get('quantization',  'int8_float16')

        self._thread    = None
        self._worker    = None
        self._success   = False

        self.setWindowTitle('BabelGG — First Run Setup')
        self.setFixedWidth(460)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )
        self.setStyleSheet(self.STYLE)
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 28, 28, 24)

        title = QLabel('Downloading Translation Engine')
        title.setObjectName('title')
        layout.addWidget(title)

        subtitle = QLabel('This happens once — about 1.5 GB')
        subtitle.setObjectName('subtitle')
        layout.addWidget(subtitle)

        layout.addSpacing(6)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat('%p%')
        layout.addWidget(self._progress)

        self._status_lbl = QLabel('Preparing...')
        self._status_lbl.setObjectName('status')
        self._status_lbl.setWordWrap(True)
        layout.addWidget(self._status_lbl)

        layout.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._retry_btn = QPushButton('Try Again')
        self._retry_btn.setObjectName('retry')
        self._retry_btn.setVisible(False)
        self._retry_btn.clicked.connect(self._start_download)
        btn_row.addWidget(self._retry_btn)

        self._cancel_btn = QPushButton('Cancel')
        self._cancel_btn.setObjectName('cancel')
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)

        layout.addLayout(btn_row)

    # ── Lifecycle ──────────────────────────────────────────────────────────
    def showEvent(self, event):
        super().showEvent(event)
        self._start_download()

    def _start_download(self):
        self._retry_btn.setVisible(False)
        self._cancel_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status_lbl.setText('Preparing...')

        self._worker = _DownloadWorker(
            self._hf_repo, self._hf_path, self._ct2_path, self._quant
        )
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.status.connect(self._status_lbl.setText)
        self._worker.finished.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        self._thread.start()

    def _on_success(self):
        self._success = True
        self._status_lbl.setText('Ready! Starting BabelGG...')
        logging.info('[DOWNLOADER] Model ready.')
        self.accept()

    def _on_error(self, msg: str):
        self._status_lbl.setText(f'Error: {msg}')
        self._retry_btn.setVisible(True)
        self._cancel_btn.setEnabled(True)
        logging.error(f'[DOWNLOADER] Error: {msg}')

    def _on_cancel(self):
        self._cancel_btn.setEnabled(False)
        self._status_lbl.setText('Cancelling...')
        if self._worker:
            self._worker.cancel()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        # Clean up partial download so next run retries cleanly
        for path in (self._ct2_path, self._hf_path):
            if os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                    logging.info(f'[DOWNLOADER] Cleaned up partial: {path}')
                except Exception as e:
                    logging.warning(f'[DOWNLOADER] Could not clean {path}: {e}')
        self.reject()


# ── Helper called from main.py ────────────────────────────────────────────────

def needs_download(version_cfg: dict) -> bool:
    """Return True if the CT2 model folder is absent or empty."""
    ct2_path = version_cfg.get('flash', {}).get('local_ct2_path', 'models/nllb-ct2')
    return not os.path.isdir(ct2_path) or not os.listdir(ct2_path)
