from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PySide6.QtCore import QRegularExpression
from typing import Dict
from .themes import get_syntax_palette


# ------------------------------
# Helper base to build formats
# ------------------------------
class _ThemeFormats:
    def __init__(self, theme_name: str):
        pal = get_syntax_palette(theme_name)
        self.fmt = {}
        for key, opts in {
            'keyword': dict(color=pal['keyword'], bold=True),
            'builtin': dict(color=pal['builtin']),
            'magic': dict(color=pal['magic']),
            'decorator': dict(color=pal['decorator']),
            'def_name': dict(color=pal['def_name'], bold=True),
            'class_name': dict(color=pal['class_name'], bold=True),
            'self_cls': dict(color=pal['self_cls'], italic=True),
            'string': dict(color=pal['string']),
            'string_doc': dict(color=pal['string_doc'], italic=True),
            'number': dict(color=pal['number']),
            'comment': dict(color=pal['comment'], italic=True),
            'import_mod': dict(color=pal['import_mod']),
            'import_name': dict(color=pal['import_name']),
            'operator': dict(color=pal['operator']),
            'punctuation': dict(color=pal['punctuation']),
            'attribute': dict(color=pal['attribute']),
            'function': dict(color=pal['function']),
            'type': dict(color=pal['type']),
            'todo': dict(color=pal['todo'], bold=True),
        }.items():
            self.fmt[key] = self._qfmt(**opts)

    @staticmethod
    def _qfmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        f = QTextCharFormat()
        f.setForeground(QColor(color))
        if bold:
            try:
                f.setFontWeight(QFont.Weight.Bold)
            except AttributeError:
                f.setFontWeight(QFont.Bold)
        if italic:
            f.setFontItalic(True)
        return f


class _BasicRegexHighlighter(QSyntaxHighlighter):
    """Lightweight regex highlighter using theme-aware formats.
    Subclasses define self._build_rules() and may use block states for multi-line constructs.
    """

    def __init__(self, parent, theme_name: str = 'eve'):
        super().__init__(parent)
        self.theme_name = theme_name
        self._formats = _ThemeFormats(theme_name).fmt
        self.simple_rules = []  # list[(QRegularExpression, QTextCharFormat)]
        self.capture_rules = []  # list[(QRegularExpression, QTextCharFormat, int)]
        self._build_rules()

    def set_theme(self, theme_name: str) -> None:
        if theme_name == self.theme_name:
            return
        self.theme_name = theme_name
        self._formats = _ThemeFormats(theme_name).fmt
        self.simple_rules.clear()
        self.capture_rules.clear()
        self._build_rules()
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt signature)
        # Subclasses may override to handle block states first
        self._highlight_with_rules(text)

    def _highlight_with_rules(self, text: str) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                s = m.capturedStart(gi)
                if s >= 0:
                    self.setFormat(s, m.capturedLength(gi), form)

    # To be implemented by subclasses
    def _build_rules(self):
        pass


# ------------------------------
# Plain Highlighter (no-op rules)
# ------------------------------
class PlainHighlighter(_BasicRegexHighlighter):
    def _build_rules(self) -> None:
        self.simple_rules = []
        self.capture_rules = []


# ------------------------------
# Python Highlighter (enhanced)
# ------------------------------
class PythonHighlighter(_BasicRegexHighlighter):
    """Theme-aware Python syntax highlighter with expanded coverage.

    Highlights:
    - keywords vs builtins
    - def/class declarations (names highlighted)
    - decorators
    - magic methods (__init__ etc.)
    - self/cls identifiers
    - imports (module vs imported names)
    - numbers (int/float/hex/bin)
    - strings (single/double) and triple-quoted docstrings
    - comments with TODO/FIXME/NOTE
    - operators and punctuation (subtle)
    - attributes (.name) and function calls (name())
    - types (Capitalized identifiers)
    """

    STATE_TRIPLE_SINGLE = 1
    STATE_TRIPLE_DOUBLE = 2

    def _build_rules(self) -> None:
        f = self._formats
        # Keywords and builtins
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
            'elif', 'else', 'except', 'False', 'finally', 'for', 'from', 'global',
            'if', 'import', 'in', 'is', 'lambda', 'None', 'nonlocal', 'not', 'or',
            'pass', 'raise', 'return', 'True', 'try', 'while', 'with', 'yield'
        ]
        builtins = [
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes', 'callable', 'chr', 'classmethod',
            'compile', 'complex', 'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec', 'filter', 'float', 'format',
            'frozenset', 'getattr', 'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance',
            'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max', 'memoryview', 'min', 'next', 'object', 'oct',
            'open', 'ord', 'pow', 'print', 'property', 'range', 'repr', 'reversed', 'round', 'set', 'setattr', 'slice',
            'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple', 'type', 'vars', 'zip'
        ]

        self.simple_rules = []
        self.capture_rules = []

        kw_re = QRegularExpression(r"\b(" + "|".join(keywords) + r")\b")
        bi_re = QRegularExpression(r"\b(" + "|".join(builtins) + r")\b")
        self.simple_rules.append((kw_re, f['keyword']))
        self.simple_rules.append((bi_re, f['builtin']))

        # Magic methods
        self.simple_rules.append((QRegularExpression(r"\b__\w+__\b"), f['magic']))
        # Decorators
        self.simple_rules.append((QRegularExpression(r"^\s*@[A-Za-z_][\w.]*"), f['decorator']))
        # self / cls identifiers
        self.simple_rules.append((QRegularExpression(r"\b(?:self|cls)\b"), f['self_cls']))
        # Comments + TODO
        self.simple_rules.append((QRegularExpression(r"#[^\n]*"), f['comment']))
        self.simple_rules.append((QRegularExpression(r"\b(?:TODO|FIXME|NOTE|BUG)\b"), f['todo']))
        # Numbers
        num_re = QRegularExpression(r"\b(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|0[oO][0-7]+|(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?)\b")
        self.simple_rules.append((num_re, f['number']))
        # Strings (single-line)
        str_sgl = QRegularExpression(r"(?i)(?:[rubf]|br|rb|fr|rf)?'([^'\\]|\\.)*'")
        str_dbl = QRegularExpression(r'(?i)(?:[rubf]|br|rb|fr|rf)?"([^"\\]|\\.)*"')
        self.simple_rules.append((str_sgl, f['string']))
        self.simple_rules.append((str_dbl, f['string']))
        # Operators and punctuation
        self.simple_rules.append((QRegularExpression(r'''(?x)
            (?:==|!=|<=|>=|<<|>>|//=|\*\*=|:=|->)|
            [=+\-*/%<>!&|^~@]
        '''), f['operator']))
        self.simple_rules.append((QRegularExpression(r"[()\[\]{}:.,;]"), f['punctuation']))
        # Attributes and calls and types
        self.capture_rules.append((QRegularExpression(r"\.(\s*[A-Za-z_]\w*)"), f['attribute'], 1))
        self.capture_rules.append((QRegularExpression(r"\b([A-Za-z_]\w*)\s*\("), f['function'], 1))
        self.capture_rules.append((QRegularExpression(r"\b([A-Z][A-Za-z0-9_]+)\b"), f['type'], 1))
        # def/class names
        self.capture_rules.append((QRegularExpression(r"\bdef\s+([A-Za-z_]\w*)"), f['def_name'], 1))
        self.capture_rules.append((QRegularExpression(r"\bclass\s+([A-Za-z_]\w*)"), f['class_name'], 1))
        # imports
        self.capture_rules.append((QRegularExpression(r"\bimport\s+([A-Za-z_][\w.]*)(?=[\s,])"), f['import_mod'], 1))
        self.capture_rules.append((QRegularExpression(r"\bfrom\s+([A-Za-z_][\w.]*)\s+import"), f['import_mod'], 1))
        self.capture_rules.append((QRegularExpression(r"\bimport\s+[A-Za-z_][\w.]*\s+as\s+([A-Za-z_]\w*)"), f['import_name'], 1))
        self.capture_rules.append((QRegularExpression(r"\bfrom\s+[A-Za-z_][\w.]*\s+import\s+([A-Za-z_]\w*)"), f['import_name'], 1))

        # Triple-quoted strings
        self._triple_single_start = QRegularExpression(r"(?i)(?:[rubf]|br|rb|fr|rf)?\'\'\'")
        self._triple_double_start = QRegularExpression(r'(?i)(?:[rubf]|br|rb|fr|rf)?"""')
        self._triple_single_end = QRegularExpression(r"\'\'\'")
        self._triple_double_end = QRegularExpression(r'"""')

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        # Handle multi-line triple-quoted strings first (docstrings)
        if self.previousBlockState() == self.STATE_TRIPLE_SINGLE:
            if self._apply_until_end(text, self._triple_single_end):
                self.setCurrentBlockState(0)
                # fall through to tokenize remainder
                rest_start = self._end_pos
                rest = text[rest_start:]
                self._highlight_with_offset(rest, rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_TRIPLE_SINGLE)
                return
        elif self.previousBlockState() == self.STATE_TRIPLE_DOUBLE:
            if self._apply_until_end(text, self._triple_double_end):
                self.setCurrentBlockState(0)
                rest_start = self._end_pos
                rest = text[rest_start:]
                self._highlight_with_offset(rest, rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_TRIPLE_DOUBLE)
                return

        # If the line is a pure comment (leading whitespace then '#'),
        # do not start triple-quoted string state even if it contains ''' or """.
        stripped = text.lstrip()
        if stripped.startswith('#'):
            self.setFormat(0, len(text), self._formats['comment'])
            self.setCurrentBlockState(0)
            return

        # Search for a new triple-quoted string start
        idx = 0
        while idx < len(text):
            ms = self._triple_single_start.match(text, idx)
            md = self._triple_double_start.match(text, idx)
            next_idx = len(text)
            which = None
            if ms.hasMatch():
                next_idx = ms.capturedStart(); which = 's'
            if md.hasMatch() and md.capturedStart() < next_idx:
                next_idx = md.capturedStart(); which = 'd'
            if which is None:
                break
            # Highlight tokens before the triple-quote
            pre = text[idx:next_idx]
            if pre:
                self._highlight_with_offset(pre, idx)
            # Now handle the triple-quote starting at next_idx
            if which == 's':
                endm = self._triple_single_end.match(text, next_idx + ms.capturedLength())
                if endm.hasMatch():
                    end_pos = endm.capturedStart() + endm.capturedLength()
                    self.setFormat(next_idx, end_pos - next_idx, self._formats['string_doc'])
                    idx = end_pos
                else:
                    self.setFormat(next_idx, len(text) - next_idx, self._formats['string_doc'])
                    self.setCurrentBlockState(self.STATE_TRIPLE_SINGLE)
                    return
            else:
                endm = self._triple_double_end.match(text, next_idx + md.capturedLength())
                if endm.hasMatch():
                    end_pos = endm.capturedStart() + endm.capturedLength()
                    self.setFormat(next_idx, end_pos - next_idx, self._formats['string_doc'])
                    idx = end_pos
                else:
                    self.setFormat(next_idx, len(text) - next_idx, self._formats['string_doc'])
                    self.setCurrentBlockState(self.STATE_TRIPLE_DOUBLE)
                    return
        # No multi-line string in this block; regular highlighting
        self.setCurrentBlockState(0)
        self._highlight_with_rules(text)

    def _apply_until_end(self, text: str, end_re: QRegularExpression) -> bool:
        m = end_re.match(text)
        if m.hasMatch():
            end_pos = m.capturedStart() + m.capturedLength()
            self.setFormat(0, end_pos, self._formats['string_doc'])
            self._end_pos = end_pos
            return True
        else:
            self.setFormat(0, len(text), self._formats['string_doc'])
            return False

    def _highlight_with_offset(self, text: str, offset: int) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                self.setFormat(offset + mm.capturedStart(), mm.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                s = mm.capturedStart(gi)
                if s >= 0:
                    self.setFormat(offset + s, mm.capturedLength(gi), form)


# ------------------------------
# JavaScript / TypeScript
# ------------------------------
class JavaScriptHighlighter(_BasicRegexHighlighter):
    STATE_ML_COMMENT = 1

    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        keywords = [
            'break','case','catch','class','const','continue','debugger','default','delete','do','else','export','extends',
            'finally','for','function','if','import','in','instanceof','new','return','super','switch','this','throw','try','typeof','var','let','void','while','with','yield','of','as','from','await'
        ]
        self.simple_rules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), f['keyword']))
        # Comments
        self.simple_rules.append((QRegularExpression(r"//[^\n]*"), f['comment']))
        # TODO/FIXME
        self.simple_rules.append((QRegularExpression(r"\b(?:TODO|FIXME|NOTE|BUG)\b"), f['todo']))
        # Numbers
        self.simple_rules.append((QRegularExpression(r"\b(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|0[oO][0-7]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b"), f['number']))
        # Strings including template literals (single-line)
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'"), f['string']))
        self.simple_rules.append((QRegularExpression(r'"([^"\\]|\\.)*"'), f['string']))
        self.simple_rules.append((QRegularExpression(r"`([^`\\]|\\.)*`"), f['string']))
        # Functions and attributes
        self.capture_rules.append((QRegularExpression(r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*\("), f['function'], 1))
        self.capture_rules.append((QRegularExpression(r"\.(\s*[A-Za-z_$][A-Za-z0-9_$]*)"), f['attribute'], 1))
        # Types (basic heuristic: PascalCase)
        self.capture_rules.append((QRegularExpression(r"\b([A-Z][A-Za-z0-9_$]+)\b"), f['type'], 1))
        # Operators, punctuation
        self.simple_rules.append((QRegularExpression(r'''(?x)
            (?:===|!==|==|!=|<=|>=|<<|>>|>>>|\+\+|--|\*=|/=|\+=|-=|&=|\|=|\^=|%=)|
            [=+\-*/%<>!&|^~?:]
        '''), f['operator']))
        self.simple_rules.append((QRegularExpression(r"[()\[\]{}:.,;]"), f['punctuation']))

        # Multi-line comments boundaries
        self._ml_comment_start = QRegularExpression(r"/\*")
        self._ml_comment_end = QRegularExpression(r"\*/")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.STATE_ML_COMMENT:
            if self._apply_until_end(text, self._ml_comment_end):
                self.setCurrentBlockState(0)
                rest_start = self._end_pos
                self._highlight_with_offset(text[rest_start:], rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        # Scan for /* */ occurrences, highlight rest normally
        idx = 0
        while idx < len(text):
            ms = self._ml_comment_start.match(text, idx)
            if not ms.hasMatch():
                break
            start = ms.capturedStart()
            # Highlight tokens before comment
            pre = text[idx:start]
            if pre:
                self._highlight_with_offset(pre, idx)
            me = self._ml_comment_end.match(text, ms.capturedEnd())
            if me.hasMatch():
                end_pos = me.capturedStart() + me.capturedLength()
                self.setFormat(start, end_pos - start, self._formats['comment'])
                idx = end_pos
            else:
                self.setFormat(start, len(text) - start, self._formats['comment'])
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        # Remainder
        self._highlight_with_offset(text[idx:], idx)
        self.setCurrentBlockState(0)

    def _apply_until_end(self, text: str, end_re: QRegularExpression) -> bool:
        m = end_re.match(text)
        if m.hasMatch():
            end_pos = m.capturedStart() + m.capturedLength()
            self.setFormat(0, end_pos, self._formats['comment'])
            self._end_pos = end_pos
            return True
        else:
            self.setFormat(0, len(text), self._formats['comment'])
            return False

    def _highlight_with_offset(self, text: str, offset: int) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                self.setFormat(offset + mm.capturedStart(), mm.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                s = mm.capturedStart(gi)
                if s >= 0:
                    self.setFormat(offset + s, mm.capturedLength(gi), form)


# ------------------------------
# JSON (and JSONC comments)
# ------------------------------
class JsonHighlighter(_BasicRegexHighlighter):
    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        # Keys: "name":  -> color the name group
        self.capture_rules.append((QRegularExpression(r'"([^"\\]|\\.)*"(?=\s*:)'), f['attribute'], 1))
        # Strings
        self.simple_rules.append((QRegularExpression('\"([^\"]|\\.)*\"'), f['string']))
        # Numbers
        self.simple_rules.append((QRegularExpression(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?"), f['number']))
        # Booleans and null
        self.simple_rules.append((QRegularExpression(r"\b(?:true|false|null)\b"), f['keyword']))
        # Comments (JSONC)
        self.simple_rules.append((QRegularExpression(r"//[^\n]*"), f['comment']))
        self._ml_comment_start = QRegularExpression(r"/\*")
        self._ml_comment_end = QRegularExpression(r"\*/")
        # Punctuation
        self.simple_rules.append((QRegularExpression(r"[{}\[\]:,]"), f['punctuation']))

    STATE_ML_COMMENT = 1

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.STATE_ML_COMMENT:
            if self._apply_until_end(text, self._ml_comment_end):
                self.setCurrentBlockState(0)
                rest_start = self._end_pos
                self._highlight_with_offset(text[rest_start:], rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        idx = 0
        while idx < len(text):
            ms = self._ml_comment_start.match(text, idx)
            if not ms.hasMatch():
                break
            start = ms.capturedStart()
            pre = text[idx:start]
            if pre:
                self._highlight_with_offset(pre, idx)
            me = self._ml_comment_end.match(text, ms.capturedEnd())
            if me.hasMatch():
                end_pos = me.capturedStart() + me.capturedLength()
                self.setFormat(start, end_pos - start, self._formats['comment'])
                idx = end_pos
            else:
                self.setFormat(start, len(text) - start, self._formats['comment'])
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        self._highlight_with_offset(text[idx:], idx)
        self.setCurrentBlockState(0)

    def _apply_until_end(self, text: str, end_re: QRegularExpression) -> bool:
        m = end_re.match(text)
        if m.hasMatch():
            end_pos = m.capturedStart() + m.capturedLength()
            self.setFormat(0, end_pos, self._formats['comment'])
            self._end_pos = end_pos
            return True
        else:
            self.setFormat(0, len(text), self._formats['comment'])
            return False

    def _highlight_with_offset(self, text: str, offset: int) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                self.setFormat(offset + mm.capturedStart(), mm.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                s = mm.capturedStart(gi)
                if s >= 0:
                    self.setFormat(offset + s, mm.capturedLength(gi), form)


# ------------------------------
# Markdown (basic)
# ------------------------------
class MarkdownHighlighter(_BasicRegexHighlighter):
    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        # Headings
        self.simple_rules.append((QRegularExpression(r"^#{1,6}\s.*"), f['def_name']))
        # Bold **text** or __text__
        self.capture_rules.append((QRegularExpression(r"\*\*([^*]+)\*\*"), f['class_name'], 1))
        self.capture_rules.append((QRegularExpression(r"__([^_]+)__"), f['class_name'], 1))
        # Italic *text* or _text_
        self.capture_rules.append((QRegularExpression(r"\*([^*]+)\*"), f['self_cls'], 1))
        self.capture_rules.append((QRegularExpression(r"_([^_]+)_"), f['self_cls'], 1))
        # Inline code `code`
        self.simple_rules.append((QRegularExpression(r"`[^`]+`"), f['string']))
        # Links [text](url)
        self.capture_rules.append((QRegularExpression(r"\[([^\]]+)\]\([^\)]+\)"), f['attribute'], 1))
        # Blockquote and list markers
        self.simple_rules.append((QRegularExpression(r"^>.*"), f['comment']))
        self.simple_rules.append((QRegularExpression(r"^(?:- |\* |\d+\. )"), f['punctuation']))
        # Fenced code blocks ```lang
        self.simple_rules.append((QRegularExpression(r"^```.*$"), f['operator']))


# ------------------------------
# YAML (basic)
# ------------------------------
class YamlHighlighter(_BasicRegexHighlighter):
    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        self.capture_rules.append((QRegularExpression(r"^(\s*)([A-Za-z0-9_-]+)(?=:)"), f['attribute'], 2))
        self.simple_rules.append((QRegularExpression(r"#[^\n]*"), f['comment']))
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""), f['string']))
        self.simple_rules.append((QRegularExpression(r"\b(?:true|false|null)\b"), f['keyword']))
        self.simple_rules.append((QRegularExpression(r"-?\b(?:0|[1-9]\d*)(?:\.\d+)?\b"), f['number']))
        self.simple_rules.append((QRegularExpression(r"[{}\[\]:,|>\-]"), f['punctuation']))
        # Anchors & aliases
        self.simple_rules.append((QRegularExpression(r"[&*][A-Za-z0-9_-]+"), f['type']))


# ------------------------------
# HTML (very basic)
# ------------------------------
class HtmlHighlighter(_BasicRegexHighlighter):
    STATE_HTML_COMMENT = 1

    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        # Tags
        self.capture_rules.append((QRegularExpression(r"<\s*([A-Za-z][A-Za-z0-9:-]*)"), f['keyword'], 1))
        self.capture_rules.append((QRegularExpression(r"</\s*([A-Za-z][A-Za-z0-9:-]*)\s*>"), f['keyword'], 1))
        # Attributes and values
        self.capture_rules.append((QRegularExpression(r"\s([A-Za-z_:][A-Za-z0-9:._-]*)\s*=\s*"), f['attribute'], 1))
        self.simple_rules.append((QRegularExpression('\"([^\"\\]|\\.)*\"|\'([^\'\\]|\\.)*\''), f['string']))
        # Punctuation
        self.simple_rules.append((QRegularExpression(r"[<>/=]"), f['punctuation']))
        # Comments
        self._c_start = QRegularExpression("<!--")
        self._c_end = QRegularExpression("-->")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.STATE_HTML_COMMENT:
            if self._apply_until_end(text, self._c_end):
                self.setCurrentBlockState(0)
                rest_start = self._end_pos
                self._highlight_with_offset(text[rest_start:], rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_HTML_COMMENT)
                return
        idx = 0
        while idx < len(text):
            ms = self._c_start.match(text, idx)
            if not ms.hasMatch():
                break
            start = ms.capturedStart()
            pre = text[idx:start]
            if pre:
                self._highlight_with_offset(pre, idx)
            me = self._c_end.match(text, ms.capturedEnd())
            if me.hasMatch():
                end_pos = me.capturedStart() + me.capturedLength()
                self.setFormat(start, end_pos - start, self._formats['comment'])
                idx = end_pos
            else:
                self.setFormat(start, len(text) - start, self._formats['comment'])
                self.setCurrentBlockState(self.STATE_HTML_COMMENT)
                return
        self._highlight_with_offset(text[idx:], idx)
        self.setCurrentBlockState(0)

    def _apply_until_end(self, text: str, end_re: QRegularExpression) -> bool:
        m = end_re.match(text)
        if m.hasMatch():
            end_pos = m.capturedStart() + m.capturedLength()
            self.setFormat(0, end_pos, self._formats['comment'])
            self._end_pos = end_pos
            return True
        else:
            self.setFormat(0, len(text), self._formats['comment'])
            return False

    def _highlight_with_offset(self, text: str, offset: int) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                self.setFormat(offset + mm.capturedStart(), mm.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                s = mm.capturedStart(gi)
                if s >= 0:
                    self.setFormat(offset + s, mm.capturedLength(gi), form)


# ------------------------------
# CSS (basic)
# ------------------------------
class CssHighlighter(_BasicRegexHighlighter):
    STATE_ML_COMMENT = 1

    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        # Selectors and properties
        self.capture_rules.append((QRegularExpression(r"(^|[{};])\s*([A-Za-z_-][A-Za-z0-9_-]*)\s*(?=:)"), f['attribute'], 2))
        # Values
        self.simple_rules.append((QRegularExpression(r"#[0-9A-Fa-f]{3,6}|\b\d+(?:px|em|rem|%|vh|vw)?\b"), f['number']))
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""), f['string']))
        # Comments
        self.simple_rules.append((QRegularExpression(r"//[^\n]*"), f['comment']))
        self._ml_comment_start = QRegularExpression(r"/\*")
        self._ml_comment_end = QRegularExpression(r"\*/")
        # Punctuation
        self.simple_rules.append((QRegularExpression(r"[{}:;,>]"), f['punctuation']))

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.STATE_ML_COMMENT:
            if self._apply_until_end(text, self._ml_comment_end):
                self.setCurrentBlockState(0)
                rest_start = self._end_pos
                self._highlight_with_offset(text[rest_start:], rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        idx = 0
        while idx < len(text):
            ms = self._ml_comment_start.match(text, idx)
            if not ms.hasMatch():
                break
            start = ms.capturedStart()
            pre = text[idx:start]
            if pre:
                self._highlight_with_offset(pre, idx)
            me = self._ml_comment_end.match(text, ms.capturedEnd())
            if me.hasMatch():
                end_pos = me.capturedStart() + me.capturedLength()
                self.setFormat(start, end_pos - start, self._formats['comment'])
                idx = end_pos
            else:
                self.setFormat(start, len(text) - start, self._formats['comment'])
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        self._highlight_with_offset(text[idx:], idx)
        self.setCurrentBlockState(0)

    def _apply_until_end(self, text: str, end_re: QRegularExpression) -> bool:
        m = end_re.match(text)
        if m.hasMatch():
            end_pos = m.capturedStart() + m.capturedLength()
            self.setFormat(0, end_pos, self._formats['comment'])
            self._end_pos = end_pos
            return True
        else:
            self.setFormat(0, len(text), self._formats['comment'])
            return False

    def _highlight_with_offset(self, text: str, offset: int) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                self.setFormat(offset + mm.capturedStart(), mm.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                s = mm.capturedStart(gi)
                if s >= 0:
                    self.setFormat(offset + s, mm.capturedLength(gi), form)


# ------------------------------
# Shell (basic)
# ------------------------------
class ShellHighlighter(_BasicRegexHighlighter):
    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        self.simple_rules.append((QRegularExpression(r"#[^\n]*"), f['comment']))
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""), f['string']))
        self.simple_rules.append((QRegularExpression(r"\b(?:if|then|else|fi|for|in|do|done|case|esac|while|function)\b"), f['keyword']))
        self.simple_rules.append((QRegularExpression(r"\$[A-Za-z_][A-Za-z0-9_]*|\${[^}]+}"), f['attribute']))
        self.simple_rules.append((QRegularExpression(r"\b-[-A-Za-z0-9_]+"), f['operator']))


# ------------------------------
# INI and TOML (basic)
# ------------------------------
class IniHighlighter(_BasicRegexHighlighter):
    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        self.simple_rules.append((QRegularExpression(r"^[;#].*"), f['comment']))
        self.simple_rules.append((QRegularExpression(r"^\[[^\]]+\]"), f['type']))
        self.capture_rules.append((QRegularExpression(r"^\s*([A-Za-z0-9_.-]+)(?=\s*=)"), f['attribute'], 1))
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""), f['string']))
        self.simple_rules.append((QRegularExpression(r"-?\b(?:0|[1-9]\d*)(?:\.\d+)?\b"), f['number']))


class TomlHighlighter(IniHighlighter):
    pass


# ------------------------------
# C-like family (C, C++, Rust, Go) — basic rules
# ------------------------------
class CHighlighter(_BasicRegexHighlighter):
    STATE_ML_COMMENT = 1

    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        keywords = [
            'auto','break','case','char','const','continue','default','do','double','else','enum','extern',
            'float','for','goto','if','inline','int','long','register','restrict','return','short','signed','sizeof',
            'static','struct','switch','typedef','union','unsigned','void','volatile','while','_Bool','_Complex','_Imaginary'
        ]
        self.simple_rules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), f['keyword']))
        # Comments
        self.simple_rules.append((QRegularExpression(r"//[^\n]*"), f['comment']))
        # Strings and numbers
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""), f['string']))
        self.simple_rules.append((QRegularExpression(r"\b(?:0[xX][0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b"), f['number']))
        # Functions and attributes (very simple)
        self.capture_rules.append((QRegularExpression(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\("), f['function'], 1))
        self.capture_rules.append((QRegularExpression(r"\.(\s*[A-Za-z_][A-Za-z0-9_]*)"), f['attribute'], 1))
        # Types heuristic (PascalCase or common C types)
        self.capture_rules.append((QRegularExpression(r"\b([A-Z][A-Za-z0-9_]+)\b"), f['type'], 1))

        self._ml_comment_start = QRegularExpression(r"/\*")
        self._ml_comment_end = QRegularExpression(r"\*/")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.STATE_ML_COMMENT:
            if self._apply_until_end(text, self._ml_comment_end):
                self.setCurrentBlockState(0)
                rest_start = self._end_pos
                self._highlight_with_offset(text[rest_start:], rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        # Scan for /* ... */
        idx = 0
        while idx < len(text):
            ms = self._ml_comment_start.match(text, idx)
            if not ms.hasMatch():
                break
            start = ms.capturedStart()
            pre = text[idx:start]
            if pre:
                self._highlight_with_offset(pre, idx)
            me = self._ml_comment_end.match(text, ms.capturedEnd())
            if me.hasMatch():
                end_pos = me.capturedStart() + me.capturedLength()
                self.setFormat(start, end_pos - start, self._formats['comment'])
                idx = end_pos
            else:
                self.setFormat(start, len(text) - start, self._formats['comment'])
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        self._highlight_with_offset(text[idx:], idx)
        self.setCurrentBlockState(0)

    def _apply_until_end(self, text: str, end_re: QRegularExpression) -> bool:
        m = end_re.match(text)
        if m.hasMatch():
            end_pos = m.capturedStart() + m.capturedLength()
            self.setFormat(0, end_pos, self._formats['comment'])
            self._end_pos = end_pos
            return True
        else:
            self.setFormat(0, len(text), self._formats['comment'])
            return False

    def _highlight_with_offset(self, text: str, offset: int) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                self.setFormat(offset + mm.capturedStart(), mm.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                s = mm.capturedStart(gi)
                if s >= 0:
                    self.setFormat(offset + s, mm.capturedLength(gi), form)


class CppHighlighter(CHighlighter):
    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        keywords = [
            'alignas','alignof','and','and_eq','asm','atomic_cancel','atomic_commit','atomic_noexcept','auto','bitand','bitor',
            'bool','break','case','catch','char','char8_t','char16_t','char32_t','class','compl','concept','const','consteval','constexpr','constinit',
            'const_cast','continue','co_await','co_return','co_yield','decltype','default','delete','do','double','dynamic_cast','else','enum','explicit',
            'export','extern','false','float','for','friend','goto','if','inline','int','long','mutable','namespace','new','noexcept','not','not_eq','nullptr',
            'operator','or','or_eq','private','protected','public','register','reinterpret_cast','requires','return','short','signed','sizeof','static',
            'static_assert','static_cast','struct','switch','template','this','thread_local','throw','true','try','typedef','typeid','typename','union',
            'unsigned','using','virtual','void','volatile','wchar_t','while','xor','xor_eq'
        ]
        self.simple_rules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), f['keyword']))
        # Comments
        self.simple_rules.append((QRegularExpression(r"//[^\n]*"), f['comment']))
        # Strings and numbers
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""), f['string']))
        self.simple_rules.append((QRegularExpression(r"\b(?:0[xX][0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b"), f['number']))
        # Templates / types heuristics
        self.capture_rules.append((QRegularExpression(r"\b([A-Z][A-Za-z0-9_]+)\b"), f['type'], 1))
        # Functions and attributes
        self.capture_rules.append((QRegularExpression(r"\b([A-Za-z_][A-Za-z0-9_:]*)\s*\("), f['function'], 1))
        self.capture_rules.append((QRegularExpression(r"\.(\s*[A-Za-z_][A-Za-z0-9_]*)"), f['attribute'], 1))

        self._ml_comment_start = QRegularExpression(r"/\*")
        self._ml_comment_end = QRegularExpression(r"\*/")


class RustHighlighter(_BasicRegexHighlighter):
    STATE_ML_COMMENT = 1

    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        keywords = [
            'as','async','await','break','const','continue','crate','dyn','else','enum','extern','false','fn','for','if','impl','in','let','loop','match','mod','move','mut','pub','ref','return','Self','self','static','struct','super','trait','true','type','unsafe','use','where','while'
        ]
        self.simple_rules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), f['keyword']))
        # Line comments (// and ///) and block comments
        self.simple_rules.append((QRegularExpression(r"//[^\n]*"), f['comment']))
        # Strings and numbers (basic)
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""), f['string']))
        self.simple_rules.append((QRegularExpression(r"\\b(?:0[xX][0-9A-Fa-f]+|\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?)\\b"), f['number']))
        # Functions and attributes / macros
        self.capture_rules.append((QRegularExpression(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*!"), f['function'], 1))  # macros like println!
        self.capture_rules.append((QRegularExpression(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\("), f['function'], 1))
        self.capture_rules.append((QRegularExpression(r"\.(\s*[A-Za-z_][A-Za-z0-9_]*)"), f['attribute'], 1))
        # Types heuristic
        self.capture_rules.append((QRegularExpression(r"\b([A-Z][A-Za-z0-9_]+)\b"), f['type'], 1))

        self._ml_comment_start = QRegularExpression(r"/\*")
        self._ml_comment_end = QRegularExpression(r"\*/")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.STATE_ML_COMMENT:
            if self._apply_until_end(text, self._ml_comment_end):
                self.setCurrentBlockState(0)
                rest_start = self._end_pos
                self._highlight_with_offset(text[rest_start:], rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        # Scan for /* ... */
        idx = 0
        while idx < len(text):
            ms = self._ml_comment_start.match(text, idx)
            if not ms.hasMatch():
                break
            start = ms.capturedStart()
            pre = text[idx:start]
            if pre:
                self._highlight_with_offset(pre, idx)
            me = self._ml_comment_end.match(text, ms.capturedEnd())
            if me.hasMatch():
                end_pos = me.capturedStart() + me.capturedLength()
                self.setFormat(start, end_pos - start, self._formats['comment'])
                idx = end_pos
            else:
                self.setFormat(start, len(text) - start, self._formats['comment'])
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        self._highlight_with_offset(text[idx:], idx)
        self.setCurrentBlockState(0)

    def _apply_until_end(self, text: str, end_re: QRegularExpression) -> bool:
        m = end_re.match(text)
        if m.hasMatch():
            end_pos = m.capturedStart() + m.capturedLength()
            self.setFormat(0, end_pos, self._formats['comment'])
            self._end_pos = end_pos
            return True
        else:
            self.setFormat(0, len(text), self._formats['comment'])
            return False

    def _highlight_with_offset(self, text: str, offset: int) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                self.setFormat(offset + mm.capturedStart(), mm.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                s = mm.capturedStart(gi)
                if s >= 0:
                    self.setFormat(offset + s, mm.capturedLength(gi), form)


class GoHighlighter(_BasicRegexHighlighter):
    STATE_ML_COMMENT = 1

    def _build_rules(self) -> None:
        f = self._formats
        self.simple_rules = []
        self.capture_rules = []
        keywords = [
            'break','case','chan','const','continue','default','defer','else','fallthrough','for','func','go','goto','if','import','interface','map','package','range','return','select','struct','switch','type','var'
        ]
        self.simple_rules.append((QRegularExpression(r"\b(" + "|".join(keywords) + r")\b"), f['keyword']))
        # Comments
        self.simple_rules.append((QRegularExpression(r"//[^\n]*"), f['comment']))
        # Strings & numbers
        self.simple_rules.append((QRegularExpression(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\""), f['string']))
        self.simple_rules.append((QRegularExpression(r"\b(?:0[xX][0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b"), f['number']))
        # Functions and attributes
        self.capture_rules.append((QRegularExpression(r"\bfunc\s+([A-Za-z_][A-Za-z0-9_]*)"), f['def_name'], 1))
        self.capture_rules.append((QRegularExpression(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\("), f['function'], 1))
        self.capture_rules.append((QRegularExpression(r"\.(\s*[A-Za-z_][A-Za-z0-9_]*)"), f['attribute'], 1))
        # Types heuristic
        self.capture_rules.append((QRegularExpression(r"\b([A-Z][A-Za-z0-9_]+)\b"), f['type'], 1))

        self._ml_comment_start = QRegularExpression(r"/\*")
        self._ml_comment_end = QRegularExpression(r"\*/")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.STATE_ML_COMMENT:
            if self._apply_until_end(text, self._ml_comment_end):
                self.setCurrentBlockState(0)
                rest_start = self._end_pos
                self._highlight_with_offset(text[rest_start:], rest_start)
                return
            else:
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        # Scan for /* ... */
        idx = 0
        while idx < len(text):
            ms = self._ml_comment_start.match(text, idx)
            if not ms.hasMatch():
                break
            start = ms.capturedStart()
            pre = text[idx:start]
            if pre:
                self._highlight_with_offset(pre, idx)
            me = self._ml_comment_end.match(text, ms.capturedEnd())
            if me.hasMatch():
                end_pos = me.capturedStart() + me.capturedLength()
                self.setFormat(start, end_pos - start, self._formats['comment'])
                idx = end_pos
            else:
                self.setFormat(start, len(text) - start, self._formats['comment'])
                self.setCurrentBlockState(self.STATE_ML_COMMENT)
                return
        self._highlight_with_offset(text[idx:], idx)
        self.setCurrentBlockState(0)

    def _apply_until_end(self, text: str, end_re: QRegularExpression) -> bool:
        m = end_re.match(text)
        if m.hasMatch():
            end_pos = m.capturedStart() + m.capturedLength()
            self.setFormat(0, end_pos, self._formats['comment'])
            self._end_pos = end_pos
            return True
        else:
            self.setFormat(0, len(text), self._formats['comment'])
            return False

    def _highlight_with_offset(self, text: str, offset: int) -> None:
        for pattern, form in self.simple_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                self.setFormat(offset + mm.capturedStart(), mm.capturedLength(), form)
        for pattern, form, gi in self.capture_rules:
            if not pattern.isValid():
                continue
            it = pattern.globalMatch(text)
            while it.hasNext():
                mm = it.next()
                s = mm.capturedStart(gi)
                if s >= 0:
                    self.setFormat(offset + s, mm.capturedLength(gi), form)


# ------------------------------
# Highlighter factory helpers
# ------------------------------
_LANGUAGE_TO_CLASS: Dict[str, type] = {
    'python': PythonHighlighter,
    'javascript': JavaScriptHighlighter,
    'typescript': JavaScriptHighlighter,
    'json': JsonHighlighter,
    'markdown': MarkdownHighlighter,
    'yaml': YamlHighlighter,
    'html': HtmlHighlighter,
    'xml': HtmlHighlighter,
    'css': CssHighlighter,
    'shell': ShellHighlighter,
    'ini': IniHighlighter,
    'toml': TomlHighlighter,
    'make': ShellHighlighter,
    'docker': ShellHighlighter,
    'c': CHighlighter,
    'cpp': CppHighlighter,
    'rust': RustHighlighter,
    'go': GoHighlighter,
    'plain': PlainHighlighter,
}


def get_highlighter_class(language: str):
    """Return PygmentsHighlighter (required). No legacy fallback.

    Raises ImportError with a clear message if Pygments is unavailable.
    """
    from .highlighters_pygments import PygmentsHighlighter, _PYGMENTS_AVAILABLE  # type: ignore
    if not _PYGMENTS_AVAILABLE:
        raise ImportError("Pygments is required for syntax highlighting")
    return PygmentsHighlighter

def create_highlighter(document, theme_name: str, language: str, file_path: str | None = None):
    """Instantiate a Pygments-backed highlighter for the given document.

    Pure Pygments: no legacy/regex or Plain fallbacks.
    """
    cls = get_highlighter_class(language)
    # Prefer 4-arg signature if supported in the Pygments bridge (future-proof),
    # otherwise use the current 3-arg signature.
    try:
        return cls(document, theme_name, language, file_path)  # type: ignore[call-arg]
    except TypeError:
        return cls(document, theme_name, language)  # type: ignore[call-arg]