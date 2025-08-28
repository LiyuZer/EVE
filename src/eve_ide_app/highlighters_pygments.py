from __future__ import annotations

from typing import Dict, Optional, List, Tuple, Any
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name
    from pygments.lexers.special import TextLexer
    from pygments.token import (
        Token, Comment, Keyword, Name, Literal, String, Number, 
        Operator, Punctuation, Error, Generic, Text
    )
    _PYGMENTS_AVAILABLE = True
except ImportError:
    _PYGMENTS_AVAILABLE = False

from .themes import get_syntax_palette

def _qfmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    try:
        f.setForeground(QColor(color))
    except Exception:
        pass
    if bold:
        try:
            f.setFontWeight(QFont.Weight.Bold)
        except AttributeError:
            f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class PygmentsHighlighter(QSyntaxHighlighter):
    """Clean, working Pygments-backed syntax highlighter."""
    
    def __init__(self, parent, theme_name: str = "eve", language: str = "plain", file_path: Optional[str] = None):
        super().__init__(parent)
        self._theme_name = theme_name or "eve"
        self._language = language or "plain"
        self._lexer = self._resolve_lexer(self._language)
        self._formats: Dict[str, QTextCharFormat] = {}
        self._rebuild_formats()
        
        # Simple cache - invalidate on document changes
        self._cached_text = ""
        self._cached_tokens: List[Tuple[int, int, QTextCharFormat]] = []

    def set_theme(self, theme_name: str) -> None:
        """Update theme and refresh highlighting."""
        new_theme = theme_name or "eve"
        if new_theme == self._theme_name:
            return
        self._theme_name = new_theme
        self._rebuild_formats()
        self._cached_text = ""  # Invalidate cache
        self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        """Qt override - highlight a single block of text."""
        if not _PYGMENTS_AVAILABLE or self._lexer is None:
            return
            
        try:
            # Get full document text for accurate lexing
            doc = self.document()
            full_text = doc.toPlainText()
            current_block = self.currentBlock()
            block_start = current_block.position()
            
            # Simple cache check
            if full_text != self._cached_text:
                self._rebuild_token_cache(full_text)
                
            # Apply cached formats to current block
            self._apply_formats_to_block(block_start, len(text))
            
        except Exception:
            # On any error, fall back to no highlighting
            pass

    def _rebuild_token_cache(self, full_text: str) -> None:
        """Rebuild token cache for entire document."""
        self._cached_text = full_text
        self._cached_tokens = []
        
        if not full_text:
            return
            
        try:
            pos = 0
            for token_type, value in lex(full_text, self._lexer):
                length = len(value)
                if length > 0:
                    fmt = self._get_format_for_token(token_type, value)
                    if fmt is not None:
                        self._cached_tokens.append((pos, length, fmt))
                pos += length
        except Exception:
            self._cached_tokens = []

    def _apply_formats_to_block(self, block_start: int, block_length: int) -> None:
        """Apply cached formats to current block."""
        block_end = block_start + block_length
        
        for token_start, token_length, fmt in self._cached_tokens:
            token_end = token_start + token_length
            
            # Skip tokens that don't overlap with current block
            if token_end <= block_start or token_start >= block_end:
                continue
                
            # Calculate intersection with current block
            format_start = max(0, token_start - block_start)
            format_end = min(block_length, token_end - block_start)
            format_length = format_end - format_start
            
            if format_length > 0:
                self.setFormat(format_start, format_length, fmt)

    def _get_format_for_token(self, token_type: Any, value: str) -> Optional[QTextCharFormat]:
        """Map Pygments token to our format."""
        # Convert token type to string for easier handling
        token_str = str(token_type)
        
        # Handle special cases first
        if 'Comment.Preproc' in token_str:
            if 'File' in token_str:
                return self._formats.get('string')
            else:
                return self._formats.get('keyword')  # #include, #define etc.
        
        # Comments
        if token_type in Comment or 'Comment' in token_str:
            return self._formats.get('comment')
            
        # Keywords
        if token_type in Keyword or 'Keyword' in token_str:
            return self._formats.get('keyword')
            
        # Strings
        if token_type in String or 'String' in token_str:
            if 'Doc' in token_str:
                return self._formats.get('string_doc')
            return self._formats.get('string')
            
        # Numbers
        if token_type in Number or 'Number' in token_str:
            return self._formats.get('number')
            
        # Names (identifiers)
        if token_type in Name or 'Name' in token_str:
            if 'Function' in token_str:
                return self._formats.get('function')
            elif 'Class' in token_str:
                return self._formats.get('class_name')
            elif 'Decorator' in token_str:
                return self._formats.get('decorator')
            elif 'Builtin' in token_str:
                if 'Pseudo' in token_str:
                    return self._formats.get('magic')
                return self._formats.get('builtin')
            elif 'Attribute' in token_str:
                return self._formats.get('attribute')
            elif 'Namespace' in token_str:
                return self._formats.get('import_mod')
            elif value and value in {'self', 'cls'}:
                return self._formats.get('self_cls')
            elif value and value[0].isupper() and value.isalpha():
                return self._formats.get('type')
                
        # Operators
        if token_type in Operator or 'Operator' in token_str:
            return self._formats.get('operator')
            
        # Punctuation
        if token_type in Punctuation or 'Punctuation' in token_str:
            return self._formats.get('punctuation')
            
        # Errors
        if token_type in Error:
            return self._formats.get('todo')  # Reuse todo format for errors
            
        return None

    def _rebuild_formats(self) -> None:
        """Rebuild format cache from theme palette."""
        pal = get_syntax_palette(self._theme_name)
        
        self._formats = {
            'keyword': _qfmt(pal.get('keyword', '#C792EA'), bold=True),
            'builtin': _qfmt(pal.get('builtin', '#82AAFF')),
            'function': _qfmt(pal.get('function', '#82AAFF')),
            'class_name': _qfmt(pal.get('class_name', '#FFCB6B'), bold=True),
            'attribute': _qfmt(pal.get('attribute', '#B2CCD6')),
            'type': _qfmt(pal.get('type', '#FFCB6B')),
            'number': _qfmt(pal.get('number', '#F78C6C')),
            'string': _qfmt(pal.get('string', '#C3E88D')),
            'string_doc': _qfmt(pal.get('string_doc', '#C3E88D'), italic=True),
            'comment': _qfmt(pal.get('comment', '#546E7A'), italic=True),
            'operator': _qfmt(pal.get('operator', '#89DDFF')),
            'punctuation': _qfmt(pal.get('punctuation', '#89DDFF')),
            'decorator': _qfmt(pal.get('decorator', '#C792EA')),
            'magic': _qfmt(pal.get('magic', '#C792EA')),
            'import_mod': _qfmt(pal.get('import_mod', '#B2CCD6')),
            'self_cls': _qfmt(pal.get('self_cls', '#B2CCD6'), italic=True),
            'todo': _qfmt(pal.get('todo', '#FF5370'), bold=True),
        }

    def _resolve_lexer(self, language: str):
        """Get Pygments lexer for language."""
        if not _PYGMENTS_AVAILABLE:
            return None
            
        # Language name mappings
        name_map = {
            'shell': 'bash',
            'sh': 'bash', 
            'zsh': 'bash',
            'fish': 'bash',
            'dockerfile': 'docker',
            'make': 'make',
            'makefile': 'make',
            'yml': 'yaml',
            'md': 'markdown',
            'jsonc': 'json',
            'jsx': 'javascript',
            'tsx': 'typescript',
        }
        
        lexer_name = name_map.get(language, language)
        
        try:
            return get_lexer_by_name(lexer_name)
        except Exception:
            try:
                return TextLexer()
            except Exception:
                return None