from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

THEMES = {
    'eve': {
        # Core palette
        'Window': QColor(18, 19, 23),         # background
        'WindowText': QColor(230, 230, 230),  # foreground
        'Base': QColor(14, 15, 19),           # editor base
        'AlternateBase': QColor(28, 30, 36),
        'ToolTipBase': Qt.white,
        'ToolTipText': Qt.black,
        'Text': QColor(230, 230, 230),
        'Button': QColor(32, 34, 40),
        'ButtonText': QColor(235, 235, 235),
        'BrightText': QColor(255, 107, 107),
        'Highlight': QColor(255, 90, 54),     # Eve flame
        'HighlightedText': Qt.black,
        'Link': QColor(255, 163, 102),
        # Accents
        'accent': '#ff5a36',
        'accent2': '#ffa366',
        'panel': '#181a20',
        'subtle': '#8a9099',
        'success': '#56d364',
        'warning': '#ffb347',
        'error': '#ff6b6b',
    },
    'dragon': {
        'Window': QColor(24, 24, 28),
        'WindowText': Qt.white,
        'Base': QColor(18, 18, 22),
        'AlternateBase': QColor(32, 32, 38),
        'ToolTipBase': Qt.white,
        'ToolTipText': Qt.black,
        'Text': Qt.white,
        'Button': QColor(36, 36, 40),
        'ButtonText': Qt.white,
        'BrightText': QColor(255, 85, 85),
        'Highlight': QColor(255, 98, 0),
        'HighlightedText': Qt.black,
        'Link': QColor(255, 140, 0),
        'accent': '#ff6200',
        'accent2': '#ffb080',
        'panel': '#20232a',
        'subtle': '#8a9099',
        'success': '#56d364',
        'warning': '#ffb347',
        'error': '#ff6b6b',
    },
    'neon': {
        # Purple/blue cyberpunk vibe (modern 2020s)
        'Window': QColor(16, 17, 22),
        'WindowText': QColor(230, 230, 230),
        'Base': QColor(12, 13, 18),
        'AlternateBase': QColor(24, 26, 32),
        'ToolTipBase': Qt.white,
        'ToolTipText': Qt.black,
        'Text': QColor(230, 230, 230),
        'Button': QColor(28, 30, 36),
        'ButtonText': QColor(235, 235, 235),
        'BrightText': QColor(255, 107, 107),
        'Highlight': QColor(139, 92, 246),  # align to accent
        'HighlightedText': Qt.black,
        'Link': QColor(34, 211, 238),
        'accent': '#8b5cf6',   # purple
        'accent2': '#22d3ee',  # cyan
        'panel': '#111217',
        'subtle': '#8a9099',
        'success': '#56d364',
        'warning': '#ffb347',
        'error': '#ff6b6b',
    },
    'light': {
        'Window': Qt.white,
        'WindowText': Qt.black,
        'Base': Qt.white,
        'AlternateBase': QColor(245, 245, 245),
        'ToolTipBase': Qt.white,
        'ToolTipText': Qt.black,
        'Text': Qt.black,
        'Button': QColor(245, 245, 245),
        'ButtonText': Qt.black,
        'BrightText': QColor(220, 0, 0),
        'Highlight': QColor(0, 120, 215),
        'HighlightedText': Qt.white,
        'Link': QColor(0, 102, 204),
        'accent': '#0078d7',
        'accent2': '#3399ff',
        'panel': '#f7f7f7',
        'subtle': '#66707b',
        'success': '#22863a',
        'warning': '#b08800',
        'error': '#d73a49',
    },
}


def apply_theme(app, theme_name: str = 'eve'):
    theme = THEMES.get(theme_name, THEMES['eve'])
    pal = QPalette()
    pal.setColor(QPalette.Window, theme['Window'])
    pal.setColor(QPalette.WindowText, theme['WindowText'])
    pal.setColor(QPalette.Base, theme['Base'])
    pal.setColor(QPalette.AlternateBase, theme['AlternateBase'])
    pal.setColor(QPalette.ToolTipBase, theme['ToolTipBase'])
    pal.setColor(QPalette.ToolTipText, theme['ToolTipText'])
    pal.setColor(QPalette.Text, theme['Text'])
    pal.setColor(QPalette.Button, theme['Button'])
    pal.setColor(QPalette.ButtonText, theme['ButtonText'])
    pal.setColor(QPalette.BrightText, theme['BrightText'])
    pal.setColor(QPalette.Highlight, theme['Highlight'])
    pal.setColor(QPalette.HighlightedText, theme['HighlightedText'])
    app.setPalette(pal)


def get_theme_colors(theme_name: str = 'eve'):
    theme = THEMES.get(theme_name, THEMES['eve'])
    return theme


def _css_color(val) -> str:
    """Return a CSS color string (#RRGGBB) for various color inputs.
    Supports QColor, Qt.GlobalColor, and hex strings.
    """
    if isinstance(val, QColor):
        return val.name()
    try:
        # Works for Qt.GlobalColor (enum/int) and hex strings
        return QColor(val).name()
    except Exception:
        # Fallback: if it looks like a string, return as-is
        try:
            n = getattr(val, 'name', None)
            if isinstance(n, str):
                # Enum name, attempt conversion via QColor again
                return QColor(val).name()
        except Exception:
            pass
        return str(val)


def apply_stylesheet(app, theme_name: str = 'eve'):
    c = get_theme_colors(theme_name)
    accent = c['accent']
    accent2 = c['accent2']
    panel = c['panel']
    subtle = c['subtle']

    text_hex = _css_color(c['Text'])
    base_hex = _css_color(c['Base'])

    css = f'''
    QMainWindow, QWidget {{ background-color: {panel}; color: {text_hex}; }}
    QToolBar {{ background: {panel}; border: none; }}
    QPlainTextEdit, QTextEdit {{ background: {base_hex}; border: 1px solid {subtle}; }}
    QTreeView {{ background: {base_hex}; border: 1px solid {subtle}; }}
    QTabWidget::pane {{ border-top: 2px solid {subtle}; }}
    QTabBar::tab {{ background: {panel}; padding: 6px 10px; border: 1px solid {subtle}; margin-right: 2px; }}
    QTabBar::tab:selected {{ background: {accent}; color: black; }}
    QPushButton {{ background: {accent}; color: black; border: 0; padding: 6px 10px; border-radius: 3px; }}
    QPushButton:disabled {{ background: {subtle}; color: #222; }}
    QLineEdit {{ background: {base_hex}; border: 1px solid {subtle}; padding: 4px; }}
    #eveHeader {{ background: {panel}; border-bottom: 1px solid {subtle}; }}
    #eveOutput {{ background: {base_hex}; border: 1px solid {subtle}; }}
    '''
    app.setStyleSheet(css)

# ==============================
# Syntax Highlighting Palettes
# ==============================

# Required keys for syntax palettes (hex color strings only)
SYNTAX_PALETTE_KEYS = [
    'keyword', 'builtin', 'magic', 'decorator', 'def_name', 'class_name', 'self_cls',
    'string', 'string_doc', 'number', 'comment', 'import_mod', 'import_name',
    'operator', 'punctuation', 'attribute', 'function', 'type', 'todo'
]

# Theme-specific syntax palettes; values must be 6-digit hex strings
# tuned for readability against each theme's Base background.
_SYNTAX_PALETTES = {
    'eve': {
        'keyword':     '#ff8c42',  # warm accent
        'builtin':     '#4ec9b0',  # teal
        'magic':       '#ffa657',  # softer accent
        'decorator':   '#c678dd',  # purple
        'def_name':    '#82aaff',  # blue
        'class_name':  '#e5c07b',  # yellow
        'self_cls':    '#73d6f5',  # light cyan
        'string':      '#ce9178',  # salmon
        'string_doc':  '#6a9955',  # greenish
        'number':      '#b5cea8',
        'comment':     '#8a9099',  # subtle
        'import_mod':  '#d19a66',  # orange-brown
        'import_name': '#4ec9b0',  # teal
        'operator':    '#c0c0c0',
        'punctuation': '#808080',
        'attribute':   '#dcdcaa',  # pale yellow
        'function':    '#82aaff',  # blue
        'type':        '#4fc1ff',  # cyan-blue
        'todo':        '#ffb454',
    },
    'dragon': {
        'keyword':     '#ff7a1a',
        'builtin':     '#3ad6c0',
        'magic':       '#ffb266',
        'decorator':   '#d19bf3',
        'def_name':    '#7abaff',
        'class_name':  '#f2cc60',
        'self_cls':    '#7fdcff',
        'string':      '#d4907c',
        'string_doc':  '#75a35f',
        'number':      '#b8d7b0',
        'comment':     '#8a9099',
        'import_mod':  '#d4956a',
        'import_name': '#3ad6c0',
        'operator':    '#c8c8c8',
        'punctuation': '#8a8a8a',
        'attribute':   '#e3e3ac',
        'function':    '#7abaff',
        'type':        '#56c7ff',
        'todo':        '#ffbf66',
    },
    'neon': {
        'keyword':     '#a78bfa',  # purple accent
        'builtin':     '#22d3ee',  # cyan
        'magic':       '#d6b3ff',
        'decorator':   '#c084fc',
        'def_name':    '#60a5fa',
        'class_name':  '#f59e0b',
        'self_cls':    '#67e8f9',
        'string':      '#fca5a5',
        'string_doc':  '#86efac',
        'number':      '#a7f3d0',
        'comment':     '#8a9099',
        'import_mod':  '#f59e0b',
        'import_name': '#22d3ee',
        'operator':    '#c7c7c7',
        'punctuation': '#999999',
        'attribute':   '#fde68a',
        'function':    '#93c5fd',
        'type':        '#38bdf8',
        'todo':        '#fbbf24',
    },
    'light': {
        'keyword':     '#005cc5',
        'builtin':     '#0b906f',
        'magic':       '#a37100',
        'decorator':   '#6f42c1',
        'def_name':    '#1a73e8',
        'class_name':  '#b08800',
        'self_cls':    '#1166a6',
        'string':      '#c41a16',
        'string_doc':  '#2b7a0b',
        'number':      '#116329',
        'comment':     '#66707b',
        'import_mod':  '#a37100',
        'import_name': '#0b906f',
        'operator':    '#666666',
        'punctuation': '#7a7a7a',
        'attribute':   '#6f6f00',
        'function':    '#1a73e8',
        'type':        '#005e8a',
        'todo':        '#b35900',
    },
}


def get_syntax_palette(theme_name: str = 'eve') -> dict:
    """Return a dict mapping SYNTAX_PALETTE_KEYS to hex color strings.
    Unknown theme names fall back to 'eve'.
    """
    theme = theme_name if theme_name in _SYNTAX_PALETTES else 'eve'
    pal = _SYNTAX_PALETTES[theme].copy()
    # Ensure all required keys are present (defensive; tests will also check)
    for k in SYNTAX_PALETTE_KEYS:
        if k not in pal:
            # If missing, supply a sane default from eve palette
            pal[k] = _SYNTAX_PALETTES['eve'][k]
    return pal