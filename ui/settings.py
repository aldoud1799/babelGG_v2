import json, logging
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QFormLayout,
    QComboBox, QSlider, QKeySequenceEdit, QPushButton,
    QHBoxLayout, QLabel, QRadioButton, QButtonGroup, QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui  import QKeySequence


SETTINGS_STYLE = """
QDialog       { background: #1A1A2E; color: #FFFFFF; font-family: 'Segoe UI'; }
QTabWidget::pane { border: 1px solid #2D3748; }
QTabBar::tab  { background: #0F3460; color: #94A3B8; padding: 8px 16px; }
QTabBar::tab:selected { background: #1A1A2E; color: #00C2A8; }
QComboBox, QKeySequenceEdit {
    background: #0F3460; color: #FFFFFF;
    border: 1px solid #2D3748; border-radius: 4px; padding: 4px;
}
QPushButton {
    background: #0F3460; color: #00C2A8; border: 1px solid #00C2A8;
    border-radius: 6px; padding: 6px 16px;
}
QPushButton:hover { background: #00C2A8; color: #000; }
QLabel { color: #CBD5E1; }
QRadioButton { color: #CBD5E1; }
QRadioButton::indicator:checked { border: 2px solid #00C2A8; background: #00C2A8; }
"""

MY_LANGUAGES = [
    'english', 'japanese', 'korean', 'chinese', 'arabic',
    'french', 'spanish', 'german', 'portuguese', 'russian',
    'thai', 'vietnamese', 'indonesian', 'turkish',
]


class SettingsWindow(QDialog):
    def __init__(self, config: dict, save_fn, parent=None):
        super().__init__(parent)
        self.config  = dict(config)   # local copy
        self.save_fn = save_fn
        self.setWindowTitle('BabelGG Settings')
        self.setFixedSize(460, 420)
        self.setStyleSheet(SETTINGS_STYLE)
        self._build()

    def _build(self):
        lay  = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._tab_general(),     'General')
        tabs.addTab(self._tab_hotkeys(),     'Hotkeys')
        tabs.addTab(self._tab_performance(), 'Performance')
        tabs.addTab(self._tab_about(),       'About')
        lay.addWidget(tabs)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _tab_general(self) -> QWidget:
        w   = QWidget()
        lay = QFormLayout(w)
        lay.setSpacing(12)
        # My language
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(MY_LANGUAGES)
        cur = self.config.get('my_language', 'english')
        idx = MY_LANGUAGES.index(cur) if cur in MY_LANGUAGES else 0
        self._lang_combo.setCurrentIndex(idx)
        lay.addRow('My Language:', self._lang_combo)
        # Card timeout
        self._timeout_slider = QSlider(Qt.Orientation.Horizontal)
        self._timeout_slider.setRange(3, 15)
        self._timeout_slider.setValue(self.config.get('card_timeout', 5))
        timeout_lbl = QLabel(f'{self._timeout_slider.value()}s')
        self._timeout_slider.valueChanged.connect(
            lambda v: timeout_lbl.setText(f'{v}s')
        )
        row = QHBoxLayout()
        row.addWidget(self._timeout_slider)
        row.addWidget(timeout_lbl)
        lay.addRow('Card Timeout:', row)
        return w

    def _tab_hotkeys(self) -> QWidget:
        w   = QWidget()
        lay = QFormLayout(w)
        lay.setSpacing(12)
        hotkeys = self.config.get('hotkeys', {})
        self._hk_toggle   = QKeySequenceEdit(QKeySequence(hotkeys.get('toggle',   'Ctrl+Shift+H')))
        self._hk_reply    = QKeySequenceEdit(QKeySequence(hotkeys.get('reply',    'Ctrl+Shift+R')))
        self._hk_settings = QKeySequenceEdit(QKeySequence(hotkeys.get('settings', 'Ctrl+Shift+,')))
        lay.addRow('Toggle BabelGG:',  self._hk_toggle)
        lay.addRow('Open Reply Box:',  self._hk_reply)
        lay.addRow('Open Settings:',   self._hk_settings)
        return w

    def _tab_performance(self) -> QWidget:
        w   = QWidget()
        lay = QFormLayout(w)
        lay.setSpacing(12)
        self._cuda_btn = QRadioButton('CUDA (GPU) — recommended')
        self._cpu_btn  = QRadioButton('CPU only — slower, 3-5s per translation')
        grp = QButtonGroup(w)
        grp.addButton(self._cuda_btn)
        grp.addButton(self._cpu_btn)
        if self.config.get('flash_device', 'cuda') == 'cuda':
            self._cuda_btn.setChecked(True)
        else:
            self._cpu_btn.setChecked(True)
        lay.addRow('Translation Device:', self._cuda_btn)
        lay.addRow('',                    self._cpu_btn)
        return w

    def _tab_about(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        lay.setSpacing(8)
        lay.addWidget(QLabel('BabelGG v0.1.0'))
        lay.addWidget(QLabel('Real-time gaming translation — copy any foreign text to translate'))
        lay.addWidget(QLabel('Translation: NLLB-200 (200 languages, fully local)'))
        lay.addWidget(QLabel('No Ollama. No external API. No subscription.'))
        return w

    def _save(self):
        self.config['my_language']  = self._lang_combo.currentText()
        self.config['card_timeout'] = self._timeout_slider.value()
        self.config['flash_device'] = 'cuda' if self._cuda_btn.isChecked() else 'cpu'
        self.config['hotkeys'] = {
            'toggle':   self._hk_toggle.keySequence().toString(),
            'reply':    self._hk_reply.keySequence().toString(),
            'settings': self._hk_settings.keySequence().toString(),
        }
        self.save_fn(self.config)
        logging.info(
            f'[SETTINGS] Saved: my_language={self.config["my_language"]} '
            f'device={self.config["flash_device"]}'
        )
        self.accept()
