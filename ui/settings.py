import logging
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QComboBox, QSlider, QKeySequenceEdit,
    QPushButton, QLabel, QRadioButton, QButtonGroup, QFrame,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui  import QKeySequence, QFont, QColor, QPalette, QIcon


# ── Palette ───────────────────────────────────────────────────────────────────
_BG       = '#0D0D1A'
_SURFACE  = '#13132A'
_CARD     = '#1A1A35'
_BORDER   = '#252545'
_ACCENT   = '#00C2A8'
_ACCENT2  = '#0097FF'
_TEXT     = '#FFFFFF'
_TEXT2    = '#8890A4'
_TEXT3    = '#505570'

STYLE = f"""
/* ── Dialog ── */
QDialog {{
    background: {_BG};
    font-family: 'Segoe UI', Arial, sans-serif;
}}

/* ── Tab bar ── */
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {_BORDER};
    background: {_BG};
}}
QTabWidget::tab-bar {{
    alignment: left;
}}
QTabBar {{
    background: {_BG};
}}
QTabBar::tab {{
    background: transparent;
    color: {_TEXT3};
    padding: 11px 22px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    text-transform: uppercase;
}}
QTabBar::tab:selected {{
    color: {_ACCENT};
    border-bottom: 2px solid {_ACCENT};
}}
QTabBar::tab:hover:!selected {{
    color: #AAAACC;
}}

/* ── Scroll / inner widgets ── */
QWidget#tab_bg {{
    background: {_BG};
}}

/* ── Section header ── */
QLabel#section {{
    color: {_TEXT3};
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
}}

/* ── Row labels ── */
QLabel#rowlabel {{
    color: {_TEXT};
    font-size: 13px;
    font-weight: 700;
}}
QLabel#rowsub {{
    color: {_TEXT2};
    font-size: 11px;
    font-weight: 400;
}}

/* ── ComboBox ── */
QComboBox {{
    background: {_CARD};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 7px 12px;
    font-size: 13px;
    font-weight: 600;
    min-width: 180px;
}}
QComboBox:hover {{
    border-color: {_ACCENT};
}}
QComboBox:focus {{
    border-color: {_ACCENT};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 28px;
    border: none;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {_ACCENT};
    width: 0; height: 0;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {_CARD};
    color: {_TEXT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    selection-background-color: {_ACCENT};
    selection-color: #000000;
    padding: 4px;
    outline: none;
}}

/* ── KeySequenceEdit ── */
QKeySequenceEdit {{
    background: {_CARD};
    color: {_ACCENT};
    border: 1px solid {_BORDER};
    border-radius: 6px;
    padding: 7px 12px;
    font-size: 13px;
    font-weight: 700;
    min-width: 180px;
}}
QKeySequenceEdit:focus {{
    border-color: {_ACCENT};
    background: #1E2040;
}}

/* ── Slider ── */
QSlider::groove:horizontal {{
    height: 4px;
    background: {_BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {_ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {_ACCENT};
    border: 2px solid {_BG};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: #00E5CC;
    width: 18px;
    height: 18px;
    margin: -7px 0;
    border-radius: 9px;
}}

/* ── Radio buttons ── */
QRadioButton {{
    color: {_TEXT};
    font-size: 13px;
    font-weight: 700;
    spacing: 10px;
}}
QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid {_BORDER};
    background: {_CARD};
}}
QRadioButton::indicator:hover {{
    border-color: {_ACCENT};
}}
QRadioButton::indicator:checked {{
    border: 2px solid {_ACCENT};
    background: {_ACCENT};
    image: none;
}}

/* ── Device cards ── */
QFrame#device_card {{
    background: {_CARD};
    border: 1px solid {_BORDER};
    border-radius: 10px;
}}
QFrame#device_card_selected {{
    background: #0D2525;
    border: 1.5px solid {_ACCENT};
    border-radius: 10px;
}}

/* ── Divider ── */
QFrame#divider {{
    background: {_BORDER};
    max-height: 1px;
    min-height: 1px;
}}

/* ── Value badge (slider value) ── */
QLabel#badge {{
    background: {_CARD};
    color: {_ACCENT};
    border: 1px solid {_BORDER};
    border-radius: 5px;
    padding: 3px 10px;
    font-size: 13px;
    font-weight: 800;
    min-width: 38px;
    qproperty-alignment: AlignCenter;
}}

/* ── About labels ── */
QLabel#about_title {{
    color: {_TEXT};
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 1px;
}}
QLabel#about_version {{
    background: {_CARD};
    color: {_ACCENT};
    border: 1px solid {_BORDER};
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 700;
}}
QLabel#about_body {{
    color: {_TEXT2};
    font-size: 12px;
    font-weight: 400;
    line-height: 1.6;
}}
QLabel#about_pill {{
    background: #0D2525;
    color: {_ACCENT};
    border: 1px solid {_ACCENT};
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 700;
}}

/* ── Footer buttons ── */
QPushButton#btn_save {{
    background: {_ACCENT};
    color: #000000;
    border: none;
    border-radius: 7px;
    padding: 9px 28px;
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.5px;
}}
QPushButton#btn_save:hover {{
    background: #00E5CC;
}}
QPushButton#btn_save:pressed {{
    background: #009E88;
}}
QPushButton#btn_cancel {{
    background: transparent;
    color: {_TEXT2};
    border: 1px solid {_BORDER};
    border-radius: 7px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#btn_cancel:hover {{
    color: {_TEXT};
    border-color: #505570;
}}
"""

MY_LANGUAGES = [
    'English', 'Japanese', 'Korean', 'Chinese', 'Arabic',
    'French', 'Spanish', 'German', 'Portuguese', 'Russian',
    'Thai', 'Vietnamese', 'Indonesian', 'Turkish',
]

LANG_FLAGS = {
    'English': '🇬🇧', 'Japanese': '🇯🇵', 'Korean': '🇰🇷', 'Chinese': '🇨🇳',
    'Arabic': '🇸🇦', 'French': '🇫🇷', 'Spanish': '🇪🇸', 'German': '🇩🇪',
    'Portuguese': '🇧🇷', 'Russian': '🇷🇺', 'Thai': '🇹🇭', 'Vietnamese': '🇻🇳',
    'Indonesian': '🇮🇩', 'Turkish': '🇹🇷',
}


def _section_header(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setObjectName('section')
    return lbl


def _divider() -> QFrame:
    line = QFrame()
    line.setObjectName('divider')
    line.setFrameShape(QFrame.Shape.HLine)
    return line


def _row_label(text: str, sub: str = '') -> QWidget:
    """Returns a vertical stack of bold label + optional subtitle."""
    w   = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    lbl = QLabel(text)
    lbl.setObjectName('rowlabel')
    lay.addWidget(lbl)
    if sub:
        s = QLabel(sub)
        s.setObjectName('rowsub')
        lay.addWidget(s)
    return w


class SettingsWindow(QDialog):
    def __init__(self, config: dict, save_fn, parent=None):
        super().__init__(parent)
        self.config  = dict(config)
        self.save_fn = save_fn
        self.setWindowTitle('BabelGG — Settings')
        self.setFixedSize(520, 500)
        self.setWindowIcon(QIcon('assets/icon.ico'))
        self.setStyleSheet(STYLE)
        self._build()

    # ── Shell ─────────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._tab_general(),     'General')
        tabs.addTab(self._tab_hotkeys(),     'Hotkeys')
        tabs.addTab(self._tab_performance(), 'Performance')
        tabs.addTab(self._tab_about(),       'About')
        root.addWidget(tabs)

        # Footer
        footer = QWidget()
        footer.setStyleSheet(f'background: {_BG}; border-top: 1px solid {_BORDER};')
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 14, 20, 14)
        fl.setSpacing(10)
        fl.addStretch()

        btn_cancel = QPushButton('Cancel')
        btn_cancel.setObjectName('btn_cancel')
        btn_cancel.setFixedHeight(38)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton('Save Changes')
        btn_save.setObjectName('btn_save')
        btn_save.setFixedHeight(38)
        btn_save.clicked.connect(self._save)

        fl.addWidget(btn_cancel)
        fl.addWidget(btn_save)
        root.addWidget(footer)

    # ── Tab: General ─────────────────────────────────────────────────────────
    def _tab_general(self) -> QWidget:
        w   = QWidget()
        w.setObjectName('tab_bg')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(0)

        # Section: Language
        lay.addWidget(_section_header('Display Language'))
        lay.addSpacing(12)

        lang_row = QHBoxLayout()
        lang_row.addWidget(_row_label('My Language', 'Text is translated into this language'))
        lang_row.addStretch()
        self._lang_combo = QComboBox()
        cur = self.config.get('my_language', 'english').capitalize()
        for lang in MY_LANGUAGES:
            self._lang_combo.addItem(f'{LANG_FLAGS.get(lang, "")}  {lang}', lang.lower())
        idx = next((i for i, l in enumerate(MY_LANGUAGES) if l.lower() == cur.lower()), 0)
        self._lang_combo.setCurrentIndex(idx)
        lang_row.addWidget(self._lang_combo)
        lay.addLayout(lang_row)

        lay.addSpacing(24)
        lay.addWidget(_divider())
        lay.addSpacing(24)

        # Section: Card
        lay.addWidget(_section_header('Translation Card'))
        lay.addSpacing(12)

        slider_row = QHBoxLayout()
        slider_row.addWidget(_row_label('Auto-dismiss Timeout', 'Card closes after this many seconds'))
        slider_row.addStretch()

        slider_inner = QHBoxLayout()
        slider_inner.setSpacing(12)
        self._timeout_slider = QSlider(Qt.Orientation.Horizontal)
        self._timeout_slider.setRange(3, 15)
        self._timeout_slider.setValue(self.config.get('card_timeout', 5))
        self._timeout_slider.setFixedWidth(140)
        self._timeout_badge = QLabel(f'{self._timeout_slider.value()}s')
        self._timeout_badge.setObjectName('badge')
        self._timeout_badge.setFixedWidth(46)
        self._timeout_slider.valueChanged.connect(
            lambda v: self._timeout_badge.setText(f'{v}s')
        )
        slider_inner.addWidget(self._timeout_slider)
        slider_inner.addWidget(self._timeout_badge)
        slider_row.addLayout(slider_inner)
        lay.addLayout(slider_row)

        lay.addStretch()
        return w

    # ── Tab: Hotkeys ─────────────────────────────────────────────────────────
    def _tab_hotkeys(self) -> QWidget:
        w   = QWidget()
        w.setObjectName('tab_bg')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(0)

        lay.addWidget(_section_header('Keyboard Shortcuts'))
        lay.addSpacing(16)

        hotkeys = self.config.get('hotkeys', {})
        self._hk_toggle   = QKeySequenceEdit(QKeySequence(hotkeys.get('toggle',   'Ctrl+Shift+H')))
        self._hk_reply    = QKeySequenceEdit(QKeySequence(hotkeys.get('reply',    'Ctrl+Shift+R')))
        self._hk_settings = QKeySequenceEdit(QKeySequence(hotkeys.get('settings', 'Ctrl+Shift+,')))

        for label, sub, widget in [
            ('Pause / Resume',  'Toggle clipboard monitoring on/off', self._hk_toggle),
            ('Open Reply Box',  'Type a reply in the sender\'s language', self._hk_reply),
            ('Open Settings',   'Open this settings window', self._hk_settings),
        ]:
            row = QHBoxLayout()
            row.addWidget(_row_label(label, sub))
            row.addStretch()
            widget.setFixedWidth(190)
            row.addWidget(widget)
            lay.addLayout(row)
            lay.addSpacing(18)

        note = QLabel('Click a field then press your desired key combination to change it.')
        note.setObjectName('rowsub')
        note.setWordWrap(True)
        lay.addSpacing(4)
        lay.addWidget(note)
        lay.addStretch()
        return w

    # ── Tab: Performance ─────────────────────────────────────────────────────
    def _tab_performance(self) -> QWidget:
        w   = QWidget()
        w.setObjectName('tab_bg')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(0)

        lay.addWidget(_section_header('Translation Device'))
        lay.addSpacing(16)

        is_cuda = self.config.get('flash_device', 'cuda') == 'cuda'

        self._cuda_btn = QRadioButton()
        self._cpu_btn  = QRadioButton()
        grp = QButtonGroup(w)
        grp.addButton(self._cuda_btn)
        grp.addButton(self._cpu_btn)
        self._cuda_btn.setChecked(is_cuda)
        self._cpu_btn.setChecked(not is_cuda)

        self._cuda_card = None
        self._cpu_card  = None

        for btn, attr, title, subtitle, badge, badge_color in [
            (self._cuda_btn, '_cuda_card', '⚡  CUDA (GPU)',
             'Uses your NVIDIA GPU — translations complete in under 1 second.',
             'RECOMMENDED', _ACCENT),
            (self._cpu_btn,  '_cpu_card',  '🖥  CPU Only',
             'No GPU required — translations may take 3–5 seconds each.',
             'SLOWER', '#FF6B6B'),
        ]:
            card = QFrame()
            card.setObjectName('device_card_selected' if btn.isChecked() else 'device_card')
            setattr(self, attr, card)
            card_lay = QHBoxLayout(card)
            card_lay.setContentsMargins(16, 14, 16, 14)
            card_lay.setSpacing(14)

            card_lay.addWidget(btn)

            text_col = QVBoxLayout()
            text_col.setSpacing(3)
            title_lbl = QLabel(title)
            title_lbl.setObjectName('rowlabel')
            sub_lbl   = QLabel(subtitle)
            sub_lbl.setObjectName('rowsub')
            text_col.addWidget(title_lbl)
            text_col.addWidget(sub_lbl)
            card_lay.addLayout(text_col)
            card_lay.addStretch()

            badge_lbl = QLabel(badge)
            badge_lbl.setStyleSheet(
                f'color: {badge_color}; background: transparent; '
                f'font-size: 10px; font-weight: 800; letter-spacing: 1px;'
            )
            card_lay.addWidget(badge_lbl)

            btn_ref = btn
            card.mousePressEvent = (lambda e, b=btn_ref: b.setChecked(True))

            lay.addWidget(card)
            lay.addSpacing(10)

        def _refresh_cards():
            for b, f in [(self._cuda_btn, self._cuda_card),
                         (self._cpu_btn,  self._cpu_card)]:
                f.setObjectName('device_card_selected' if b.isChecked() else 'device_card')
                f.setStyleSheet('')

        self._cuda_btn.toggled.connect(lambda _: _refresh_cards())

        lay.addStretch()
        return w

    # ── Tab: About ───────────────────────────────────────────────────────────
    def _tab_about(self) -> QWidget:
        w   = QWidget()
        w.setObjectName('tab_bg')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(0)

        title = QLabel('BabelGG')
        title.setObjectName('about_title')
        lay.addWidget(title)
        lay.addSpacing(6)

        ver_row = QHBoxLayout()
        ver_row.setSpacing(8)
        ver = QLabel(f'v{self.config.get("version", "0.1.0")}')
        ver.setObjectName('about_version')
        ver_row.addWidget(ver)
        ver_row.addStretch()
        lay.addLayout(ver_row)

        lay.addSpacing(18)
        lay.addWidget(_divider())
        lay.addSpacing(16)

        desc = QLabel(
            'Real-time gaming translation. Copy any foreign text to your clipboard\n'
            'and BabelGG instantly translates it — no browser, no alt-tab.'
        )
        desc.setObjectName('about_body')
        desc.setWordWrap(True)
        lay.addWidget(desc)

        lay.addSpacing(20)

        model_lbl = QLabel('Translation Model')
        model_lbl.setObjectName('section')
        lay.addWidget(model_lbl)
        lay.addSpacing(10)

        model_desc = QLabel(
            'NLLB-200 Distilled 600M — Meta AI\n'
            '200 languages  ·  Fully local  ·  No cloud calls'
        )
        model_desc.setObjectName('about_body')
        lay.addWidget(model_desc)

        lay.addSpacing(20)

        pills_row = QHBoxLayout()
        pills_row.setSpacing(8)
        for pill_text in ['No Ollama', 'No API Key', 'No Subscription', 'Offline']:
            p = QLabel(pill_text)
            p.setObjectName('about_pill')
            pills_row.addWidget(p)
        pills_row.addStretch()
        lay.addLayout(pills_row)

        lay.addStretch()
        return w

    # ── Save ─────────────────────────────────────────────────────────────────
    def _save(self):
        self.config['my_language']  = self._lang_combo.currentData()
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
