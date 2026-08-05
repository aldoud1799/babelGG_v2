"""
ui/downloader.py

First-run model setup for CT2 runtime.
Downloads NLLB source artifacts and prepares the required CT2 profile
(CPU or CUDA) based on startup device selection.
"""
import logging
import os
import threading
import time
import hashlib
import math
import urllib.request
import urllib.error
import traceback

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton

from core.paths import asset_path, base_path, models_path


_DOWNLOAD_CHUNK_SIZE = 8 * 1024 * 1024
_UI_UPDATE_INTERVAL_S = 0.25
_PARALLEL_WORKERS = 4
_PARALLEL_MIN_SIZE = 256 * 1024 * 1024


def _resolve_config_path(path_value: str) -> str:
    if os.path.isabs(path_value):
        return path_value

    norm = str(path_value or '').replace('\\', '/').strip('./')
    if norm.startswith('models/'):
        sub = norm.split('/', 1)[1]
        return models_path(*[p for p in sub.split('/') if p])
    if norm == 'models':
        return models_path()
    return base_path(*[p for p in norm.split('/') if p])


def _gguf_is_valid(path: str) -> bool:
    return os.path.isfile(path) and os.path.getsize(path) > 300 * 1024 * 1024


def _ct2_model_is_ready(model_dir: str) -> bool:
    return os.path.isfile(os.path.join(model_dir, 'model.bin'))


def _model_dir_candidates(path_value: str) -> list[str]:
    """Return candidate directories across bundled and user-writable roots."""
    if os.path.isabs(path_value):
        return [path_value]

    norm = str(path_value or '').replace('\\', '/').strip('./')
    if not norm:
        return []

    candidates: list[str] = []
    if norm.startswith('models/'):
        sub = [p for p in norm.split('/', 1)[1].split('/') if p]
        candidates.append(base_path('models', *sub))
        candidates.append(models_path(*sub))
    elif norm == 'models':
        candidates.append(base_path('models'))
        candidates.append(models_path())
    else:
        candidates.append(base_path(*[p for p in norm.split('/') if p]))

    # Stable de-dup preserving order
    seen = set()
    deduped = []
    for c in candidates:
        key = os.path.normcase(os.path.normpath(c))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped


def _any_ct2_model_ready(path_value: str) -> bool:
    for model_dir in _model_dir_candidates(path_value):
        if _ct2_model_is_ready(model_dir):
            return True
    return False


def _friendly_download_error(exc: Exception) -> str:
    raw = str(exc) or exc.__class__.__name__
    msg = raw.lower()
    if 'timed out' in msg or 'timeout' in msg:
        return 'Network timeout while contacting HuggingFace. Check connection and retry.'
    if 'connection' in msg or 'dns' in msg or 'name or service not known' in msg:
        return 'Unable to reach HuggingFace. Check internet/firewall settings and retry.'
    if '401' in msg or '403' in msg:
        return 'Access to model repository was denied. Verify repository visibility/permissions.'
    if '404' in msg or 'not found' in msg:
        return 'Requested model repository or artifact was not found.'
    if 'disk' in msg or 'no space' in msg:
        return 'Insufficient disk space for model download. Free space and retry.'
    return f'Download failed: {raw}'


def _error_with_type(exc: Exception) -> str:
    return f'{exc.__class__.__name__}: {exc}'


def _safe_log_exception(prefix: str, exc: Exception):
    # Never let logging failures hide the real download error.
    try:
        logging.error('%s %s', prefix, _error_with_type(exc))
        logging.debug('%s traceback:\n%s', prefix, traceback.format_exc())
    except Exception:
        pass


class _DownloadWorker(QObject):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(
        self,
        repo_id: str,
        hf_model_dir: str,
        ct2_cpu_dir: str,
        ct2_gpu_dir: str,
        required_device: str,
        hf_token: str | None = None,
    ):
        super().__init__()
        self._repo_id = repo_id
        self._hf_model_dir = hf_model_dir
        self._ct2_cpu_dir = ct2_cpu_dir
        self._ct2_gpu_dir = ct2_gpu_dir
        self._required_device = 'cuda' if str(required_device or '').lower().strip() == 'cuda' else 'cpu'
        self._hf_token = (hf_token or '').strip()
        self._cancel = threading.Event()

    def _auth_headers(self) -> dict:
        if not self._hf_token:
            return {}
        return {'Authorization': f'Bearer {self._hf_token}'}

    @staticmethod
    def _fmt_rate(rate_bps: float) -> str:
        return f'{max(0.0, rate_bps) / (1024 * 1024):.2f} MB/s'

    def cancel(self):
        self._cancel.set()

    def _sleep_with_cancel(self, seconds: int):
        for _ in range(max(0, seconds * 10)):
            if self._cancel.is_set():
                return
            time.sleep(0.1)

    def run(self):
        try:
            target_dir = self._ct2_gpu_dir if self._required_device == 'cuda' else self._ct2_cpu_dir
            if _ct2_model_is_ready(target_dir):
                self.progress.emit(100)
                self.status.emit('Model already present.')
                self.finished.emit()
                return

            self.progress.emit(5)
            self.status.emit('Preparing model setup...')
            os.makedirs(self._hf_model_dir, exist_ok=True)
            os.makedirs(self._ct2_cpu_dir, exist_ok=True)
            os.makedirs(self._ct2_gpu_dir, exist_ok=True)

            if self._cancel.is_set():
                return

            self.progress.emit(20)
            self.status.emit('Downloading model artifacts from HuggingFace...')

            from huggingface_hub import snapshot_download

            snapshot_download(
                repo_id=self._repo_id,
                local_dir=self._hf_model_dir,
                local_dir_use_symlinks=False,
                token=(self._hf_token or None),
                resume_download=True,
            )

            if self._cancel.is_set():
                return

            self.progress.emit(60)

            import ctranslate2

            converter = ctranslate2.converters.TransformersConverter(self._hf_model_dir)
            if self._required_device == 'cuda':
                self.status.emit('Converting model to CTranslate2 (CUDA)...')
                converter.convert(self._ct2_gpu_dir, quantization='int8_float16', force=True)
                if not _ct2_model_is_ready(self._ct2_gpu_dir):
                    raise RuntimeError('CUDA CT2 conversion finished but model.bin was not created.')
            else:
                self.status.emit('Converting model to CTranslate2 (CPU)...')
                converter.convert(self._ct2_cpu_dir, quantization='int8', force=True)
                if not _ct2_model_is_ready(self._ct2_cpu_dir):
                    raise RuntimeError('CPU CT2 conversion finished but model.bin was not created.')

            self.progress.emit(100)
            self.status.emit('Model setup complete.')
            self.finished.emit()
        except Exception as e:
            if not self._cancel.is_set():
                _safe_log_exception('[DOWNLOADER] Fatal error:', e)
                self.error.emit(f'{_friendly_download_error(e)} ({_error_with_type(e)})')


class DownloaderDialog(QDialog):
    STYLE = """
        QDialog { background: #1A1A2E; }
        QLabel#title { color: #FFFFFF; font-size: 16px; font-weight: bold; }
        QLabel#subtitle { color: #A0A0B0; font-size: 12px; }
        QLabel#status { color: #00C2A8; font-size: 12px; }
        QProgressBar {
            background: #2A2A4E;
            border: 1px solid #3A3A5E;
            border-radius: 4px;
            height: 18px;
            text-align: center;
            color: #FFFFFF;
            font-size: 11px;
        }
        QProgressBar::chunk { background: #00C2A8; border-radius: 3px; }
        QPushButton#cancel {
            background: #2A2A4E;
            color: #A0A0B0;
            border: 1px solid #3A3A5E;
            border-radius: 4px;
            padding: 6px 20px;
            font-size: 12px;
        }
        QPushButton#cancel:hover { background: #3A2A4E; color: #FFFFFF; }
        QPushButton#retry {
            background: #00C2A8;
            color: #000000;
            border: none;
            border-radius: 4px;
            padding: 6px 20px;
            font-size: 12px;
            font-weight: bold;
        }
        QPushButton#retry:hover { background: #00E0C0; }
    """

    def __init__(self, version_cfg: dict, required_device: str = 'cpu', parent=None):
        super().__init__(parent)

        flash = version_cfg.get('flash', {})
        self._repo_id = flash.get('repo', 'facebook/nllb-200-distilled-600M')
        self._hf_token = flash.get('hf_token') or None
        self._required_device = 'cuda' if str(required_device or '').lower().strip() == 'cuda' else 'cpu'
        rel_hf = flash.get('local_hf_path') or 'models/nllb-200-distilled-600M'
        rel_ct2_gpu = flash.get('local_ct2_gpu_path') or 'models/nllb-ct2-gpu'
        rel_ct2 = flash.get('local_ct2_cpu_path') or flash.get('local_ct2_path') or 'models/nllb-ct2-cpu'
        self._hf_model_dir = _resolve_config_path(rel_hf)
        self._ct2_gpu_dir = _resolve_config_path(rel_ct2_gpu)
        self._ct2_cpu_dir = _resolve_config_path(rel_ct2)

        self._thread = None
        self._worker = None

        self.setWindowTitle('BabelGG — First Run Setup')
        self.setFixedWidth(460)
        self.setWindowIcon(QIcon(asset_path('traylogo.png')))
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )
        self.setStyleSheet(self.STYLE)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 28, 28, 24)

        title = QLabel('Downloading Translation Model')
        title.setObjectName('title')
        layout.addWidget(title)

        target = 'CUDA model' if self._required_device == 'cuda' else 'CPU model'
        subtitle = QLabel(f'One-time setup: NLLB {target} download and conversion')
        subtitle.setObjectName('subtitle')
        layout.addWidget(subtitle)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat('%p%')
        layout.addWidget(self._progress)

        self._status_lbl = QLabel('Preparing...')
        self._status_lbl.setObjectName('status')
        self._status_lbl.setWordWrap(True)
        layout.addWidget(self._status_lbl)

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

    def showEvent(self, event):
        super().showEvent(event)
        self._start_download()

    def _start_download(self):
        self._retry_btn.setVisible(False)
        self._cancel_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status_lbl.setText('Preparing...')

        self._worker = _DownloadWorker(
            self._repo_id,
            self._hf_model_dir,
            self._ct2_cpu_dir,
            self._ct2_gpu_dir,
            self._required_device,
            hf_token=self._hf_token,
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
        self._status_lbl.setText('Ready! Starting BabelGG...')
        logging.info('[DOWNLOADER] CT2 %s model ready.', self._required_device)
        self.accept()

    def _on_error(self, msg: str):
        self._status_lbl.setText(f'Error: {msg}')
        self._retry_btn.setVisible(True)
        self._cancel_btn.setEnabled(True)
        logging.error('[DOWNLOADER] Error: %s', msg)

    def _on_cancel(self):
        self._cancel_btn.setEnabled(False)
        self._status_lbl.setText('Cancelling...')
        if self._worker:
            self._worker.cancel()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        self.reject()


def needs_download(version_cfg: dict, required_device: str | None = None) -> bool:
    flash = version_cfg.get('flash', {})
    gpu_rel = flash.get('local_ct2_gpu_path') or 'models/nllb-ct2-gpu'
    cpu_rel = flash.get('local_ct2_cpu_path') or flash.get('local_ct2_path') or 'models/nllb-ct2-cpu'

    gpu_ready = _any_ct2_model_ready(gpu_rel)
    cpu_ready = _any_ct2_model_ready(cpu_rel)

    device = str(required_device or '').lower().strip()
    if device == 'cpu':
        return not cpu_ready
    if device == 'cuda':
        # CUDA mode requires a CUDA-ready CT2 model profile.
        return not gpu_ready

    return not (gpu_ready or cpu_ready)

