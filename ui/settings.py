import logging
from PyQt6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QComboBox, QSlider, QKeySequenceEdit,
    QPushButton, QLabel, QRadioButton, QButtonGroup, QFrame, QCheckBox,
    QSizePolicy, QSpacerItem, QMessageBox, QLineEdit, QScrollArea,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui  import QKeySequence, QFont, QColor, QPalette, QIcon
from core.paths import asset_path
from core.i18n import APP_LANGUAGE_OPTIONS, TRANSLATION_LANGUAGE_OPTIONS, normalize_app_language, tr
import webbrowser
import json


# ── Palette ───────────────────────────────────────────────────────────────────
_BG       = '#141414'
_SURFACE  = '#1E1E1E'
_CARD     = '#262626'
_BORDER   = '#3A3A3A'
_ACCENT   = '#E5E5E5'
_ACCENT2  = '#FFFFFF'
_TEXT     = '#FFFFFF'
_TEXT2    = '#AAAAAA'
_TEXT3    = '#666666'

STYLE = f"""
/* ── Dialog ── */
QDialog {{
    background: {_BG};
    font-family: 'Roboto', 'Segoe UI', Arial, sans-serif;
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
    padding: 12px 22px;
    font-size: 12px;
    font-weight: 650;
    letter-spacing: 0.4px;
    border: none;
    border-bottom: 2px solid transparent;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
    text-transform: none;
}}
QTabBar::tab:selected {{
    color: #FFFFFF;
    background: rgba(255, 255, 255, 0.08);
    border-bottom: 2px solid {_ACCENT};
}}
QTabBar::tab:hover:!selected {{
    color: #CCCCCC;
}}

/* ── Scroll / inner widgets ── */
QWidget#tab_bg {{
    background: {_BG};
}}

/* ── Section header ── */
QLabel#section {{
    color: {_TEXT3};
    font-size: 10px;
    font-weight: 900;
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
    border-radius: 9px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 700;
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
    border-radius: 9px;
    selection-background-color: {_ACCENT};
    selection-color: #000000;
    padding: 4px;
    outline: none;
}}

/* ── KeySequenceEdit ── */
QKeySequenceEdit {{
    background: {_CARD};
    color: #FFFFFF;
    border: 1px solid {_BORDER};
    border-radius: 9px;
    padding: 8px 12px;
    font-size: 13px;
    font-weight: 700;
    min-width: 180px;
}}
QKeySequenceEdit:focus {{
    border-color: {_ACCENT};
    background: #2A2A2A;
}}

/* ── Slider ── */
QSlider::groove:horizontal {{
    height: 4px;
    background: #333333;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {_ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {_BG};
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: #FFFFFF;
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
    border-color: #888888;
}}
QRadioButton::indicator:checked {{
    border: 2px solid #E5E5E5;
    background: #E5E5E5;
    image: none;
}}

/* ── Device cards ── */
QFrame#device_card {{
    background: {_CARD};
    border: 1px solid {_BORDER};
    border-radius: 12px;
}}
QFrame#device_card_selected {{
    background: #2A2A2A;
    border: 1.5px solid #E5E5E5;
    border-radius: 12px;
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
    color: #FFFFFF;
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 3px 10px;
    font-size: 13px;
    font-weight: 900;
    min-width: 38px;
    qproperty-alignment: AlignCenter;
}}

/* ── About labels ── */
QLabel#about_title {{
    color: {_TEXT};
    font-size: 22px;
    font-weight: 900;
    letter-spacing: 1px;
}}
QLabel#about_version {{
    background: {_CARD};
    color: #FFFFFF;
    border: 1px solid {_BORDER};
    border-radius: 7px;
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
    background: #2A2A2A;
    color: #FFFFFF;
    border: 1px solid #444444;
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 700;
}}

/* ── Footer buttons ── */
QPushButton#btn_save {{
    background: {_ACCENT};
    color: #000000;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 10px;
    padding: 9px 28px;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 0.5px;
}}
QPushButton#btn_save:hover {{
    background: #FFFFFF;
    color: #000000;
}}
QPushButton#btn_save:pressed {{
    background: #CCCCCC;
    color: #000000;
}}
QPushButton#btn_cancel {{
    background: transparent;
    color: {_TEXT2};
    border: 1px solid {_BORDER};
    border-radius: 10px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#btn_cancel:hover {{
    color: {_TEXT};
    border-color: #666666;
}}
"""

LANG_FLAGS_BY_CODE = {
    'english': '🇬🇧',
    'japanese': '🇯🇵',
    'korean': '🇰🇷',
    'chinese': '🇨🇳',
    'arabic': '🇸🇦',
    'french': '🇫🇷',
    'spanish': '🇪🇸',
    'german': '🇩🇪',
    'portuguese': '🇧🇷',
    'russian': '🇷🇺',
    'thai': '🇹🇭',
    'vietnamese': '🇻🇳',
    'indonesian': '🇮🇩',
    'turkish': '🇹🇷',
    'italian': '🇮🇹',
    'dutch': '🇳🇱',
    'polish': '🇵🇱',
    'swedish': '🇸🇪',
    'hindi': '🇮🇳',
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
    lbl.setWordWrap(True)
    lay.addWidget(lbl)
    if sub:
        s = QLabel(sub)
        s.setObjectName('rowsub')
        s.setWordWrap(True)
        lay.addWidget(s)
    return w


class SettingsWindow(QDialog):
    def __init__(self, config: dict, save_fn, license_manager=None, on_license_changed=None, telemetry=None, parent=None):
        super().__init__(parent)
        self.config  = dict(config)
        self._app_lang = normalize_app_language(self.config.get('app_language', 'english'))
        self.save_fn = save_fn
        self.license_manager = license_manager
        self.on_license_changed = on_license_changed
        self.telemetry = telemetry
        self.setWindowTitle(self._t('settings_title', 'BabelGG - Settings'))
        self.setMinimumSize(720, 560)
        self.resize(920, 680)
        self.setWindowIcon(QIcon(asset_path('traylogo.png')))
        self.setStyleSheet(STYLE)
        self._build()

    def _t(self, key: str, default: str, **kwargs) -> str:
        return tr(key, default, lang=self._app_lang, **kwargs)

    # ── Shell ─────────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setUsesScrollButtons(True)
        self._tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self._tabs.tabBar().setExpanding(False)
        self._tabs.addTab(self._wrap_tab(self._tab_general()),     self._t('tab_general', 'General'))
        self._tabs.addTab(self._wrap_tab(self._tab_hotkeys()),     self._t('tab_hotkeys', 'Hotkeys'))
        self._tabs.addTab(self._wrap_tab(self._tab_performance()), self._t('tab_performance', 'Performance'))
        self._tabs.addTab(self._wrap_tab(self._tab_about()),       self._t('tab_about', 'About'))
        self._tabs.addTab(self._wrap_tab(self._tab_pro()),         self._t('tab_pro', 'Pro'))
        self._tabs.addTab(self._wrap_tab(self._tab_privacy()),     self._t('tab_privacy', 'Privacy'))
        root.addWidget(self._tabs)

        # Footer
        footer = QWidget()
        footer.setStyleSheet(f'background: {_BG}; border-top: 1px solid {_BORDER};')
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 14, 20, 14)
        fl.setSpacing(10)
        fl.addStretch()

        btn_cancel = QPushButton(self._t('btn_cancel', 'Cancel'))
        btn_cancel.setObjectName('btn_cancel')
        btn_cancel.setFixedHeight(38)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton(self._t('btn_save_changes', 'Save Changes'))
        btn_save.setObjectName('btn_save')
        btn_save.setFixedHeight(38)
        btn_save.clicked.connect(self._save)

        fl.addWidget(btn_cancel)
        fl.addWidget(btn_save)
        root.addWidget(footer)

    def _wrap_tab(self, content: QWidget) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        return scroll

    # ── Tab: General ─────────────────────────────────────────────────────────
    def _tab_general(self) -> QWidget:
        w   = QWidget()
        w.setObjectName('tab_bg')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(0)

        # Section: Language
        lay.addWidget(_section_header(self._t('section_language', 'Language')))
        lay.addSpacing(12)

        auto_lang_row = QHBoxLayout()
        auto_lang_row.addWidget(
            _row_label(
                self._t('label_auto_language', 'Auto Language'),
                self._t(
                    'label_auto_language_sub',
                    'Follow PC language automatically for app and translation target',
                ),
            )
        )
        auto_lang_row.addStretch()
        self._auto_lang_toggle = QCheckBox(self._t('checkbox_enabled', 'Enabled'))
        self._auto_lang_toggle.setChecked(bool(self.config.get('language_auto_detect', True)))
        self._auto_lang_toggle.toggled.connect(self._refresh_language_controls)
        auto_lang_row.addWidget(self._auto_lang_toggle)
        lay.addLayout(auto_lang_row)

        lay.addSpacing(16)

        app_lang_row = QHBoxLayout()
        app_lang_row.addWidget(
            _row_label(
                self._t('label_app_language', 'App Language'),
                self._t('label_app_language_sub', 'Language used in the app interface'),
            )
        )
        app_lang_row.addStretch()
        self._app_lang_combo = QComboBox()
        current_app_lang = normalize_app_language(self.config.get('app_language', 'english'))
        app_idx = 0
        for idx, (code, label) in enumerate(APP_LANGUAGE_OPTIONS):
            flag = LANG_FLAGS_BY_CODE.get(code, '')
            self._app_lang_combo.addItem(f'{flag}  {label}', code)
            if code == current_app_lang:
                app_idx = idx
        self._app_lang_combo.setCurrentIndex(app_idx)
        self._app_lang_combo.setMinimumWidth(220)
        app_lang_row.addWidget(self._app_lang_combo)
        lay.addLayout(app_lang_row)

        lay.addSpacing(16)

        lang_row = QHBoxLayout()
        lang_row.addWidget(
            _row_label(
                self._t('label_my_language', 'My Translation Language'),
                self._t('label_my_language_sub', 'Incoming text will be translated into this language'),
            )
        )
        lang_row.addStretch()
        self._lang_combo = QComboBox()
        current_lang = str(self.config.get('my_language', 'english')).strip().lower()
        idx = 0
        for i, (code, label) in enumerate(TRANSLATION_LANGUAGE_OPTIONS):
            self._lang_combo.addItem(f'{LANG_FLAGS_BY_CODE.get(code, "")}  {label}', code)
            if code == current_lang:
                idx = i
        self._lang_combo.setCurrentIndex(idx)
        self._lang_combo.setMinimumWidth(220)
        lang_row.addWidget(self._lang_combo)
        lay.addLayout(lang_row)
        self._refresh_language_controls()

        lay.addSpacing(24)
        lay.addWidget(_divider())
        lay.addSpacing(24)

        # Section: Card
        lay.addWidget(_section_header(self._t('section_translation_card', 'Translation Card')))
        lay.addSpacing(12)

        slider_row = QHBoxLayout()
        slider_row.addWidget(
            _row_label(
                self._t('label_card_timeout', 'Auto-dismiss Timeout'),
                self._t('label_card_timeout_sub', 'Card closes after this many seconds'),
            )
        )
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

        lay.addSpacing(16)

        anchor_row = QHBoxLayout()
        anchor_row.addWidget(
            _row_label(
                self._t('label_card_anchor', 'Card Anchor'),
                self._t('label_card_anchor_sub', 'Choose where cards appear on screen'),
            )
        )
        anchor_row.addStretch()
        self._anchor_combo = QComboBox()
        self._anchor_combo.addItem(self._t('anchor_top_left', 'Top Left'), 'top_left')
        self._anchor_combo.addItem(self._t('anchor_top_right', 'Top Right'), 'top_right')
        self._anchor_combo.addItem(self._t('anchor_bottom_left', 'Bottom Left'), 'bottom_left')
        self._anchor_combo.addItem(self._t('anchor_bottom_right', 'Bottom Right'), 'bottom_right')
        cur_anchor = str(self.config.get('card_anchor', 'bottom_right')).lower()
        idx_anchor = next((i for i in range(self._anchor_combo.count())
                           if self._anchor_combo.itemData(i) == cur_anchor), 3)
        self._anchor_combo.setCurrentIndex(idx_anchor)
        self._anchor_combo.setMinimumWidth(220)
        anchor_row.addWidget(self._anchor_combo)
        lay.addLayout(anchor_row)

        lay.addSpacing(16)

        rate_row = QHBoxLayout()
        rate_row.addWidget(
            _row_label(
                self._t('label_card_rate_limit', 'Card Rate Limit'),
                self._t('label_card_rate_limit_sub', 'Minimum delay between shown cards'),
            )
        )
        rate_row.addStretch()

        rate_inner = QHBoxLayout()
        rate_inner.setSpacing(12)
        self._rate_slider = QSlider(Qt.Orientation.Horizontal)
        self._rate_slider.setRange(0, 30)  # 0.0s..3.0s
        cur_rate = float(self.config.get('card_rate_limit_s', 0.0))
        self._rate_slider.setValue(int(max(0, min(30, round(cur_rate * 10)))))
        self._rate_slider.setFixedWidth(140)
        self._rate_badge = QLabel(f'{self._rate_slider.value() / 10:.1f}s')
        self._rate_badge.setObjectName('badge')
        self._rate_badge.setFixedWidth(52)
        self._rate_slider.valueChanged.connect(
            lambda v: self._rate_badge.setText(f'{v / 10:.1f}s')
        )
        rate_inner.addWidget(self._rate_slider)
        rate_inner.addWidget(self._rate_badge)
        rate_row.addLayout(rate_inner)
        lay.addLayout(rate_row)

        lay.addSpacing(16)

        compact_row = QHBoxLayout()
        compact_row.addWidget(
            _row_label(
                self._t('label_compact_mode', 'Compact Mode'),
                self._t('label_compact_mode_sub', 'Show a shorter, less intrusive translation card'),
            )
        )
        compact_row.addStretch()
        self._compact_toggle = QCheckBox(self._t('checkbox_enabled', 'Enabled'))
        self._compact_toggle.setChecked(bool(self.config.get('card_compact', True)))
        compact_row.addWidget(self._compact_toggle)
        lay.addLayout(compact_row)

        lay.addSpacing(24)
        lay.addWidget(_divider())
        lay.addSpacing(16)

        preset_row = QHBoxLayout()
        preset_row.addWidget(
            _row_label(
                self._t('label_gaming_presets', 'Gaming Presets'),
                self._t('label_gaming_presets_sub', 'Preferred style preset for gameplay translations'),
            )
        )
        preset_row.addStretch()

        self._preset_combo = QComboBox()
        for label, value in [
            (self._t('preset_balanced', 'Balanced'), 'balanced'),
            (self._t('preset_aggressive', 'Aggressive'), 'aggressive'),
            (self._t('preset_friendly', 'Friendly'), 'friendly'),
        ]:
            self._preset_combo.addItem(label, value)
        cur_preset = str(self.config.get('gaming_preset', 'balanced')).lower()
        idx = next((i for i in range(self._preset_combo.count()) if self._preset_combo.itemData(i) == cur_preset), 0)
        self._preset_combo.setCurrentIndex(idx)
        self._preset_combo.setMinimumWidth(220)

        if not self._license_is_pro():
            self._preset_combo.setEnabled(False)
            self._preset_combo.setToolTip(self._t('tooltip_pro_upgrade', '🔒 Pro feature - upgrade to unlock'))
            lock_lbl = QLabel(self._t('label_pro_locked_short', '🔒 Pro'))
            lock_lbl.setStyleSheet('color: #D97706; font-size: 10px; font-weight: 900;')
            preset_row.addWidget(lock_lbl)

        preset_row.addWidget(self._preset_combo)
        lay.addLayout(preset_row)

        lay.addStretch()
        return w

    # ── Tab: Hotkeys ─────────────────────────────────────────────────────────
    def _tab_hotkeys(self) -> QWidget:
        w   = QWidget()
        w.setObjectName('tab_bg')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(0)

        lay.addWidget(_section_header(self._t('section_keyboard_shortcuts', 'Keyboard Shortcuts')))
        lay.addSpacing(16)

        hotkeys = self.config.get('hotkeys', {})
        self._hk_toggle   = QKeySequenceEdit(QKeySequence(hotkeys.get('toggle',   'Ctrl+Shift+H')))
        self._hk_reply    = QKeySequenceEdit(QKeySequence(hotkeys.get('reply',    'Ctrl+Shift+R')))
        self._hk_settings = QKeySequenceEdit(QKeySequence(hotkeys.get('settings', 'Ctrl+Shift+Comma')))
        self._hk_ocr      = QKeySequenceEdit(QKeySequence(hotkeys.get('ocr',      'Ctrl+Shift+G')))
        self._hk_reshow   = QKeySequenceEdit(QKeySequence(hotkeys.get('reshow',   'Ctrl+Shift+T')))

        for label, sub, widget in [
            (
                self._t('hk_pause_resume', 'Pause / Resume'),
                self._t('hk_pause_resume_sub', 'Toggle clipboard monitoring on/off'),
                self._hk_toggle,
            ),
            (
                self._t('hk_open_reply', 'Open Reply Box'),
                self._t('hk_open_reply_sub', "Type a reply in the sender's language"),
                self._hk_reply,
            ),
            (
                self._t('hk_open_settings', 'Open Settings'),
                self._t('hk_open_settings_sub', 'Open this settings window'),
                self._hk_settings,
            ),
            (
                self._t('hk_ocr_capture', 'OCR Capture'),
                self._t('hk_ocr_capture_sub', 'Capture on-screen text area'),
                self._hk_ocr,
            ),
            (
                self._t('hk_reshow_last', 'Re-show Last Card'),
                self._t('hk_reshow_last_sub', 'Show the last translation card again'),
                self._hk_reshow,
            ),
        ]:
            row = QHBoxLayout()
            row.addWidget(_row_label(label, sub))
            row.addStretch()
            widget.setMinimumWidth(210)
            widget.setMaximumWidth(340)
            row.addWidget(widget)
            lay.addLayout(row)
            lay.addSpacing(18)

        note = QLabel(self._t('hk_note', 'Click a field then press your desired key combination to change it.'))
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

        lay.addWidget(_section_header(self._t('section_translation_device', 'Translation Device')))
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
            (
                self._cuda_btn,
                '_cuda_card',
                self._t('device_cuda_title', '⚡  CUDA (GPU)'),
                self._t('device_cuda_sub', 'Uses your NVIDIA GPU — translations complete in under 1 second.'),
                self._t('device_cuda_badge', 'RECOMMENDED'),
                '#FFFFFF',
            ),
            (
                self._cpu_btn,
                '_cpu_card',
                self._t('device_cpu_title', '🖥  CPU Only'),
                self._t('device_cpu_sub', 'No GPU required — translations may take 3–5 seconds each.'),
                self._t('device_cpu_badge', 'SLOWER'),
                '#FF6B6B',
            ),
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
                f'font-size: 10px; font-weight: 900; letter-spacing: 1px;'
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

        lay.addSpacing(8)
        lay.addWidget(_divider())
        lay.addSpacing(16)

        natural_row = QHBoxLayout()
        natural_row.addWidget(
            _row_label(
                self._t('label_natural_mode', 'Natural Mode'),
                self._t('label_natural_mode_sub', 'More natural translations (Pro feature)'),
            )
        )
        natural_row.addStretch()
        self._natural_toggle = QCheckBox(
            self._t('label_natural_mode_toggle', 'Natural Mode — more natural translations')
        )
        self._natural_toggle.setChecked(bool(self.config.get('natural_mode', True)))
        if not self._license_is_pro():
            self._natural_toggle.setEnabled(False)
            self._natural_toggle.setToolTip(self._t('tooltip_pro_upgrade', '🔒 Pro feature - upgrade to unlock'))
            lock_lbl = QLabel(self._t('label_pro_locked_short', '🔒 Pro'))
            lock_lbl.setStyleSheet('color: #D97706; font-size: 10px; font-weight: 900;')
            natural_row.addWidget(lock_lbl)
        natural_row.addWidget(self._natural_toggle)
        lay.addLayout(natural_row)

        lay.addStretch()
        return w

    # ── Tab: About ───────────────────────────────────────────────────────────
    def _tab_about(self) -> QWidget:
        w   = QWidget()
        w.setObjectName('tab_bg')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(0)

        title = QLabel(self._t('about_brand', 'BabelGG'))
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

        desc = QLabel(self._t(
            'about_desc',
            'Real-time gaming translation. Copy any foreign text to your clipboard\n'
            'and BabelGG instantly translates it — no browser, no alt-tab.',
        ))
        desc.setObjectName('about_body')
        desc.setWordWrap(True)
        lay.addWidget(desc)

        lay.addSpacing(14)
        extra = QLabel(
            self._t(
                'about_extra',
                'Configure translation behavior, hotkeys, performance, privacy, and Pro features from the tabs above.',
            )
        )
        extra.setObjectName('about_body')
        extra.setWordWrap(True)
        lay.addWidget(extra)

        lay.addStretch()
        return w

    # ── Tab: Pro ─────────────────────────────────────────────────────────────
    def _tab_pro(self) -> QWidget:
        w = QWidget()
        w.setObjectName('tab_bg')
        self._pro_root = QVBoxLayout(w)
        self._pro_root.setContentsMargins(24, 20, 24, 20)
        self._pro_root.setSpacing(12)
        self._render_pro_tab()
        return w

    def _clear_layout(self, layout: QVBoxLayout):
        while layout.count():
            item = layout.takeAt(0)
            child = item.widget()
            if child is not None:
                child.deleteLater()

    def _license_is_pro(self) -> bool:
        return bool(self.license_manager and self.license_manager.is_pro())

    def _render_pro_tab(self):
        self._clear_layout(self._pro_root)
        is_pro = self._license_is_pro()

        title = QLabel(
            self._t('pro_title_active', 'BabelGG Pro ✓')
            if is_pro
            else self._t('pro_title_upgrade', 'Upgrade to BabelGG Pro')
        )
        title.setObjectName('about_title')
        self._pro_root.addWidget(title)

        subtitle = QLabel(
            self._t('pro_subtitle_active', 'Status: Active on this machine')
            if is_pro
            else self._t('pro_subtitle_upgrade', 'Unlock Natural mode, History, and more')
        )
        subtitle.setObjectName('about_body')
        subtitle.setWordWrap(True)
        self._pro_root.addWidget(subtitle)

        if is_pro and self.license_manager:
            lic = self.license_manager.get_data()
            plan = str(lic.get('plan', 'pro')).capitalize()
            plan_lbl = QLabel(self._t('pro_plan_label', 'Plan: {plan}', plan=plan))
            plan_lbl.setObjectName('about_version')
            self._pro_root.addWidget(plan_lbl)
        else:
            self._pro_root.addWidget(_divider())
            for feat in [
                self._t('pro_feature_natural', '🔒 Natural Mode (better translations)'),
                self._t('pro_feature_history', '🔒 Translation History'),
                self._t('pro_feature_presets', '🔒 Gaming Presets'),
            ]:
                row = QLabel(feat)
                row.setObjectName('rowlabel')
                self._pro_root.addWidget(row)

            self._pro_root.addSpacing(8)
            pricing = QLabel(self._t('pro_pricing', 'Pro Monthly: $4.99/month\nPro Lifetime: $29 once'))
            pricing.setObjectName('about_body')
            pricing.setWordWrap(True)
            self._pro_root.addWidget(pricing)

        self._pro_root.addSpacing(8)
        actions = QHBoxLayout()

        if is_pro:
            btn_manage = QPushButton(self._t('btn_manage_license', 'Manage License'))
            btn_manage.setObjectName('btn_cancel')
            btn_manage.clicked.connect(lambda: webbrowser.open('https://babelgg.gg/pro'))

            btn_deactivate = QPushButton(self._t('btn_deactivate', 'Deactivate'))
            btn_deactivate.setObjectName('btn_save')
            btn_deactivate.clicked.connect(self._on_deactivate_license)

            actions.addWidget(btn_manage)
            actions.addWidget(btn_deactivate)
        else:
            btn_get = QPushButton(self._t('btn_get_pro', 'Get Pro →'))
            btn_get.setObjectName('btn_save')
            btn_get.clicked.connect(lambda: webbrowser.open('https://babelgg.gg/pro'))
            actions.addWidget(btn_get)

        actions.addStretch()
        self._pro_root.addLayout(actions)

        if not is_pro:
            self._pro_root.addSpacing(10)
            self._pro_root.addWidget(
                _row_label(
                    self._t('pro_have_key_title', 'Already have a key?'),
                    self._t('pro_have_key_sub', 'Enter your BabelGG license key below'),
                )
            )
            self._license_key = QLineEdit()
            self._license_key.setPlaceholderText(self._t('pro_key_placeholder', 'BABELGG-XXXX-XXXX-XXXX'))
            self._license_key.setStyleSheet(
                f'background: {_CARD}; color: {_TEXT}; border: 1px solid {_BORDER}; '
                'border-radius: 6px; padding: 8px 10px; font-size: 12px;'
            )
            self._pro_root.addWidget(self._license_key)

            key_row = QHBoxLayout()
            activate_btn = QPushButton(self._t('btn_activate', 'Activate'))
            activate_btn.setObjectName('btn_save')
            activate_btn.clicked.connect(self._on_activate_license)
            key_row.addWidget(activate_btn)
            key_row.addStretch()
            self._pro_root.addLayout(key_row)

        self._pro_msg = QLabel('')
        self._pro_msg.setObjectName('rowsub')
        self._pro_msg.setWordWrap(True)
        self._pro_root.addWidget(self._pro_msg)
        self._pro_root.addStretch()

    def _notify_license_change(self):
        if callable(self.on_license_changed) and self.license_manager:
            self.on_license_changed(self.license_manager.is_pro())

    def _on_activate_license(self):
        if not self.license_manager:
            self._pro_msg.setText(self._t('msg_license_manager_unavailable', 'License manager unavailable'))
            return
        key = self._license_key.text().strip() if hasattr(self, '_license_key') else ''
        result = self.license_manager.activate(key)
        self._pro_msg.setText(
            result.get('message', self._t('msg_activation_result_unavailable', 'Activation result unavailable'))
        )
        self._notify_license_change()
        if result.get('success'):
            self._render_pro_tab()

    def _on_deactivate_license(self):
        if not self.license_manager:
            self._pro_msg.setText(self._t('msg_license_manager_unavailable', 'License manager unavailable'))
            return
        reply = QMessageBox.question(
            self,
            self._t('dialog_deactivate_title', 'Deactivate License'),
            self._t('dialog_deactivate_body', 'Deactivate Pro on this machine and free one activation slot?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok = self.license_manager.deactivate()
        self._notify_license_change()
        self._pro_msg.setText(
            self._t('msg_license_deactivated', 'License deactivated')
            if ok
            else self._t('msg_license_deactivate_failed', 'Could not deactivate right now')
        )
        if ok:
            self._render_pro_tab()

    # ── Tab: Privacy ─────────────────────────────────────────────────────────
    def _tab_privacy(self) -> QWidget:
        w = QWidget()
        w.setObjectName('tab_bg')
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        lay.addWidget(_section_header(self._t('section_privacy', 'Privacy')))
        lay.addWidget(
            _row_label(
                self._t('privacy_local_usage_title', 'Local Usage Stats'),
                self._t('privacy_local_usage_sub', 'Stored on your machine only. Used to improve phrase suggestions.'),
            )
        )

        self._telemetry_local_toggle = QCheckBox(
            self._t('privacy_local_usage_toggle', 'Store local usage statistics')
        )
        self._telemetry_local_toggle.setChecked(bool(self.config.get('telemetry_local_enabled', True)))
        lay.addWidget(self._telemetry_local_toggle)

        btn_row = QHBoxLayout()
        view_btn = QPushButton(self._t('btn_view_report', 'View Report'))
        view_btn.setObjectName('btn_cancel')
        view_btn.clicked.connect(self._view_telemetry_report)

        clear_btn = QPushButton(self._t('btn_clear_data', 'Clear Data'))
        clear_btn.setObjectName('btn_cancel')
        clear_btn.clicked.connect(self._clear_telemetry_data)
        btn_row.addWidget(view_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addSpacing(8)
        self._cloud_opt_in = QCheckBox(
            self._t('privacy_cloud_optin', 'Help improve BabelGG (opt-in, coming soon)')
        )
        self._cloud_opt_in.setChecked(bool(self.config.get('telemetry_cloud_opt_in', False)))
        self._cloud_opt_in.setEnabled(False)
        self._cloud_opt_in.setToolTip(self._t('coming_soon', 'Coming soon'))
        lay.addWidget(self._cloud_opt_in)

        coming = QLabel(
            self._t('privacy_coming', 'Sends anonymous signals to improve translation quality. (Coming soon)')
        )
        coming.setObjectName('rowsub')
        coming.setWordWrap(True)
        lay.addWidget(coming)

        self._privacy_msg = QLabel('')
        self._privacy_msg.setObjectName('rowsub')
        self._privacy_msg.setWordWrap(True)
        lay.addWidget(self._privacy_msg)

        lay.addSpacing(8)
        lay.addWidget(_divider())
        lay.addSpacing(8)

        privacy_btn_row = QHBoxLayout()
        privacy_btn_row.addStretch()

        privacy_policy_btn = QPushButton(self._t('btn_privacy_policy', 'Privacy Policy'))
        privacy_policy_btn.setObjectName('btn_cancel')
        privacy_policy_btn.clicked.connect(self._open_privacy_policy)
        privacy_btn_row.addWidget(privacy_policy_btn)

        export_logs_btn = QPushButton(self._t('btn_export_logs', 'Export Logs'))
        export_logs_btn.setObjectName('btn_cancel')
        export_logs_btn.clicked.connect(self._export_logs)
        privacy_btn_row.addWidget(export_logs_btn)

        lay.addLayout(privacy_btn_row)
        lay.addStretch()
        return w

    def _view_telemetry_report(self):
        if not self.telemetry:
            self._privacy_msg.setText(self._t('msg_telemetry_unavailable', 'Telemetry unavailable'))
            return
        report = self.telemetry.get_quality_report()
        gaps = self.telemetry.get_phrase_gaps()
        body = {
            'quality_report': report,
            'phrase_gaps': gaps,
        }
        QMessageBox.information(
            self,
            self._t('dialog_local_telemetry_report', 'Local Telemetry Report'),
            json.dumps(body, indent=2, ensure_ascii=False),
        )

    def _clear_telemetry_data(self):
        if not self.telemetry:
            self._privacy_msg.setText(self._t('msg_telemetry_unavailable', 'Telemetry unavailable'))
            return
        self.telemetry.clear_data()
        self._privacy_msg.setText(self._t('msg_telemetry_cleared', 'Telemetry data cleared'))

    def _open_privacy_policy(self):
        import os
        from core.paths import data_path
        privacy_path = os.path.join(os.path.dirname(data_path()), 'PRIVACY.md')
        if os.path.isfile(privacy_path):
            webbrowser.open(f'file://{privacy_path}')
        else:
            webbrowser.open('https://github.com/aldoud1799/babelGG_v2/blob/main/PRIVACY.md')

    def _export_logs(self):
        import os, subprocess
        from core.paths import data_path
        log_dir = data_path()
        if os.path.isdir(log_dir):
            subprocess.run(['explorer', log_dir], check=False)

    # ── Save ─────────────────────────────────────────────────────────────────
    def _save(self):
        def _seq_or_default(seq_edit, default: str) -> str:
            seq = seq_edit.keySequence().toString().strip()
            return seq or default

        self.config['my_language']  = self._lang_combo.currentData()
        self.config['app_language'] = self._app_lang_combo.currentData()
        self.config['language_auto_detect'] = bool(self._auto_lang_toggle.isChecked())
        self.config['card_timeout'] = self._timeout_slider.value()
        self.config['card_anchor']  = self._anchor_combo.currentData()
        self.config['card_compact'] = bool(self._compact_toggle.isChecked())
        self.config['gaming_preset'] = self._preset_combo.currentData()
        self.config['card_rate_limit_s'] = round(self._rate_slider.value() / 10.0, 1)
        self.config['flash_device'] = 'cuda' if self._cuda_btn.isChecked() else 'cpu'
        self.config['natural_mode'] = bool(self._natural_toggle.isChecked())
        self.config['telemetry_local_enabled'] = bool(self._telemetry_local_toggle.isChecked())
        self.config['hotkeys'] = {
            'toggle':   _seq_or_default(self._hk_toggle, 'Ctrl+Shift+H'),
            'reply':    _seq_or_default(self._hk_reply, 'Ctrl+Shift+R'),
            'settings': _seq_or_default(self._hk_settings, 'Ctrl+Shift+Comma'),
            'ocr':      _seq_or_default(self._hk_ocr, 'Ctrl+Shift+G'),
            'reshow':   _seq_or_default(self._hk_reshow, 'Ctrl+Shift+T'),
        }
        self.save_fn(self.config)
        logging.info(
            f'[SETTINGS] Saved: my_language={self.config["my_language"]} '
            f'device={self.config["flash_device"]}'
        )
        self.accept()

    def _refresh_language_controls(self):
        auto_enabled = bool(getattr(self, '_auto_lang_toggle', None) and self._auto_lang_toggle.isChecked())
        if hasattr(self, '_app_lang_combo'):
            self._app_lang_combo.setEnabled(not auto_enabled)
        if hasattr(self, '_lang_combo'):
            self._lang_combo.setEnabled(not auto_enabled)
