from __future__ import annotations
from typing import Optional
from PySide6.QtCore import QSettings, QByteArray

ORG = 'Eve'
APP = 'EveIDE'


class AppSettings:
    def __init__(self):
        self.s = QSettings(ORG, APP)

    # ----- Workspace -----
    def last_project(self) -> Optional[str]:
        return self.s.value('last_project', type=str)

    def set_last_project(self, path: str):
        self.s.setValue('last_project', path)

    # ----- Theme -----
    def theme(self) -> str:
        return self.s.value('theme', 'eve', type=str)

    def set_theme(self, name: str):
        self.s.setValue('theme', name)

    # ----- Window geometry -----
    def save_geometry(self, geo: QByteArray, state: QByteArray):
        self.s.setValue('win/geometry', geo)
        self.s.setValue('win/state', state)

    def load_geometry(self) -> tuple[Optional[QByteArray], Optional[QByteArray]]:
        return (
            self.s.value('win/geometry', None, type=QByteArray),
            self.s.value('win/state', None, type=QByteArray),
        )

    # ----- Autocomplete Preferences -----
    def autocomplete_enabled(self) -> bool:
        return self.s.value('ac/enabled', True, type=bool)

    def set_autocomplete_enabled(self, enabled: bool) -> None:
        self.s.setValue('ac/enabled', bool(enabled))

    def autocomplete_debounce_ms(self) -> int:
        # Lower default for a modern, fast feel
        return self.s.value('ac/debounce_ms', 90, type=int)

    def set_autocomplete_debounce_ms(self, ms: int) -> None:
        self.s.setValue('ac/debounce_ms', int(ms))

    def autocomplete_completion_length(self) -> int:
        return self.s.value('ac/completion_length', 50, type=int)

    def set_autocomplete_completion_length(self, n: int) -> None:
        self.s.setValue('ac/completion_length', int(n))

    def autocomplete_model(self) -> str:
        # Align with current deployment default
        return self.s.value('ac/model', 'gpt-4.1-nano', type=str)

    def set_autocomplete_model(self, model: str) -> None:
        self.s.setValue('ac/model', model or 'gpt-4.1-nano')

    def autocomplete_show_inline_hints(self) -> bool:
        return self.s.value('ac/show_inline_hints', True, type=bool)

    def set_autocomplete_show_inline_hints(self, show: bool) -> None:
        self.s.setValue('ac/show_inline_hints', bool(show))

    def autocomplete_partial_accept_enabled(self) -> bool:
        return self.s.value('ac/partial_accept', False, type=bool)

    def set_autocomplete_partial_accept_enabled(self, enabled: bool) -> None:
        self.s.setValue('ac/partial_accept', bool(enabled))