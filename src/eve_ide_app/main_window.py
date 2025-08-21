from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QFileDialog, QMessageBox, QApplication,
    QToolBar, QLabel, QStyle, QTabWidget, QToolButton, QMenu, QInputDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QAction, QKeySequence
from PySide6 import QtGui

from .file_explorer import FileExplorer
from .editor import TabManager, CodeEditor
from .terminal_widget import TerminalWidget
from .eve_interface import EveInterfaceWidget
from .settings import AppSettings
from .themes_modern import (
    apply_theme as apply_theme_new,
    apply_stylesheet as apply_stylesheet_new,
)
from .project_wizard import NewProjectDialog
from .icon_provider import EveIconProvider
from .search_panel import SearchPanel
import subprocess
import json
import time
import os
import sys
import shutil
from .ac_client import sync_health
from .splash import get_logo_path




def _mode_for_theme(name: str) -> str:
    """Return icon mode: 'light' if theme name contains 'light', else 'dark'."""
    n = (name or '').lower()
    return 'light' if 'light' in n else 'dark'


def _normalize_theme(name: str | None) -> str:
    """Normalize theme name to one of: 'eve', 'dragon', 'light'."""
    n = (name or 'eve').lower()
    if 'light' in n:
        return 'light'
    if n == 'neon' or 'eve' in n:
        return 'eve'
    return 'dragon'


def _modern_key(name: str) -> str:
    """Map normalized theme to modern style key used by themes_modern."""
    base = _normalize_theme(name)
    return {
        'eve': 'eve_modern',
        'dragon': 'dragon_modern',
        'light': 'light_modern',
    }[base]
class MainWindow(QMainWindow):
    def __init__(self, initial_root: str | Path | None = None):
        super().__init__()
        self.setWindowTitle('Eve IDE — Autonomous Coding Dragon')
        self.settings = AppSettings()

        # Determine project root and server script absolute path
        project_root = Path(__file__).resolve().parents[2]
        server_script = project_root / 'autocomplete.py'

        # Prepare environment for autocomplete server:
        # Use real mode only if a Fireworks key is present; otherwise run in test mode for snappy ghost text
        env = os.environ.copy()
        have_fw = bool(env.get('FIREWORKS_API_KEY'))
        if not have_fw and not env.get('EVE_AUTOCOMPLETE_TEST'):
            env['EVE_AUTOCOMPLETE_TEST'] = '1'

        # Remove stale server_info.json files to avoid latching onto an old port
        primary_info = project_root / 'server_info.json'
        fallback_info = project_root / 'src' / 'server_info.json'
        for _p in (primary_info, fallback_info):
            try:
                if _p.exists():
                    _p.unlink()
            except Exception:
                pass
        # Run autocomplete.py in the background (non-blocking handshake), unless disabled via env
        skip_ac = bool(os.environ.get('EVE_DISABLE_AUTOCOMPLETE'))
        bypass_ac = False
        # Fast-path in test mode: write handshake and set port without spawning a server
        try:
            if env.get('EVE_AUTOCOMPLETE_TEST'):
                try:
                    import socket
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('', 0))
                        p = s.getsockname()[1]
                except Exception:
                    p = 37517
                info = {
                    'port': int(p),
                    'pid': 0,
                    'started_at': time.time(),
                    'mode': 'test',
                }
                # Write to both primary and fallback locations
                for _path in (primary_info, fallback_info):
                    try:
                        with open(_path, 'w', encoding='utf-8') as f:
                            json.dump(info, f)
                            try:
                                f.flush()
                                os.fsync(f.fileno())
                            except Exception:
                                pass
                    except Exception:
                        pass
                self.auto_completion_pid = 0
                self.auto_completion_port = int(p)
                try:
                    self.statusBar().showMessage(f'Autocomplete Ready Test (:{p})')
                except Exception:
                    pass
                bypass_ac = True
        except Exception:
            pass

        if not skip_ac and not bypass_ac:
            try:
                # Prefer the exact interpreter running the app; fallback to python3/python
                py = sys.executable or ''
                if not py or not os.path.exists(py):
                    py = shutil.which('python3') or shutil.which('python') or 'python3'
                process = subprocess.Popen(
                    [py, str(server_script)],
                    stdout=subprocess.DEVNULL,   # avoid PIPE backpressure deadlocks
                    stderr=subprocess.DEVNULL,
                    cwd=str(project_root),       # ensure server_info.json is written to project root
                    env=env,
                )
                self.auto_completion_pid = process.pid or 0
            except Exception:
                self.auto_completion_pid = 0
            self.auto_completion_port = 0

            # Poll server_info.json for up to 6s without blocking the UI
            try:
                info_candidates = [primary_info, fallback_info]
                deadline = time.monotonic() + 6.0
                self._ac_timer = QTimer(self)
                self._ac_timer.setInterval(50)

                def _poll_server_info():
                    # File-based handshake
                    try:
                        for info_path in info_candidates:
                            if info_path.exists():
                                with info_path.open('r', encoding='utf-8') as f:
                                    data = json.load(f)
                                p = int((data.get('port') or 0))
                                # Accept as soon as a port is written (health check deferred)
                                if p > 0:
                                    self.auto_completion_port = p
                                    mode = (data.get('mode', '') or '').strip()
                                    try:
                                        if mode:
                                            self.statusBar().showMessage(f'Autocomplete Ready {mode.capitalize()} (:{p})')
                                        else:
                                            self.statusBar().showMessage(f'Autocomplete Ready (:{p})')
                                    except Exception:
                                        pass
                                    # Propagate port to already-open editors and trigger a first completion
                                    try:
                                        for i in range(self.tab_manager.count()):
                                            w = self.tab_manager.widget(i)
                                            if hasattr(w, 'auto_completion_port'):
                                                w.auto_completion_port = p
                                                try:
                                                    # Kick off an initial completion so suggestions appear without waiting
                                                    if hasattr(w, '_on_cursor_changed'):
                                                        w._on_cursor_changed()
                                                except Exception:
                                                    pass
                                    except Exception:
                                        pass
                                    self._ac_timer.stop()
                                    return
                    except Exception:
                        pass

                    if time.monotonic() > deadline:
                        try:
                            self.statusBar().showMessage('Autocomplete Unavailable')
                        except Exception:
                            pass
                        self._ac_timer.stop()

                self._ac_timer.timeout.connect(_poll_server_info)
                self._ac_timer.start()
            except Exception:
                # Fall back quietly; IDE remains usable without autocomplete
                pass
        elif skip_ac:
            # Autocomplete explicitly disabled (tests/CI or user preference)
            self.auto_completion_pid = 0
            self.auto_completion_port = 0
            try:
                self.statusBar().showMessage('Autocomplete Disabled')
            except Exception:
                pass
        # Central layout: left explorer, right (editor over terminal)
        self.file_explorer = FileExplorer()
        self.tab_manager = TabManager()
        self.terminal = TerminalWidget()
        self.eve_panel = EveInterfaceWidget()
        self.search_panel = SearchPanel()

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.terminal, "Terminal")
        self.bottom_tabs.addTab(self.eve_panel, "Eve")
        self.bottom_tabs.addTab(self.search_panel, "Search")

        # When search result is chosen, open file and jump to location
        self.search_panel.openLocation.connect(self._open_location_from_search)

        right_split = QSplitter(Qt.Vertical)
        right_split.addWidget(self.tab_manager)
        right_split.addWidget(self.bottom_tabs)
        right_split.setStretchFactor(0, 3)
        right_split.setStretchFactor(1, 1)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.file_explorer)
        split.addWidget(right_split)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)

        self.setCentralWidget(split)

        # Actions and toolbar
        tb = QToolBar('Main Toolbar')
        tb.setObjectName('main_toolbar')
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(tb)

        # Build minimal actions and wire them
        self._set_toolbar_icons(tb)
        # Build File menu with Open File, Open Folder (current window), New Window
        self._build_menu_bar()

        # Global find/replace actions and shortcuts
        self._install_find_actions()

        # Logo in toolbar/status
        try:
            logo_path = get_logo_path()
        except Exception:
            logo_path = None
        if logo_path:
            # Always set window icon to the dragon
            self.setWindowIcon(QIcon(str(logo_path)))
            # Show a tiny toolbar dragon only if explicitly enabled via env
            try:
                v = (os.environ.get("EVE_TOOLBAR_LOGO") or "").strip().lower()
                show_toolbar_logo = v in {"1", "true", "on", "yes"}
            except Exception:
                show_toolbar_logo = False
            if show_toolbar_logo:
                # Optional height in px (default 24)
                try:
                    h = int((os.environ.get("EVE_TOOLBAR_LOGO_PX") or "24").strip())
                    h = max(12, min(128, h))
                except Exception:
                    h = 24
                lbl = QLabel()
                pix = QPixmap(str(logo_path)).scaledToHeight(h, Qt.SmoothTransformation)
                lbl.setPixmap(pix)
                tb.addWidget(lbl)

        # Context indicator in status bar so updates are safe
        try:
            self.context_indicator = QLabel('Context: 0')
            # Permanent widget keeps it aligned to the right of the status bar
            self.statusBar().addPermanentWidget(self.context_indicator)
        except Exception:
            # Fallback: attach to toolbar if status bar is unavailable
            try:
                self.context_indicator = QLabel('Context: 0')
                tb.addWidget(self.context_indicator)
            except Exception:
                # Last resort: create the attribute to avoid AttributeError
                self.context_indicator = QLabel('Context: 0')
        self.statusBar().showMessage('Ready')

        # Wiring
        self.file_explorer.fileOpenRequested.connect(self._open_file_path)
        try:
            self.eve_panel.contextSizeChanged.connect(self._on_context_size)
        except Exception:
            pass
        try:
            self.tab_manager.currentChanged.connect(self._on_tab_changed)
            self.tab_manager.editorCreated.connect(self._register_editor)
        except Exception:
            pass

        # Restore settings
        geo, state = self.settings.load_geometry()
        if geo:
            self.restoreGeometry(geo)
        if state:
            self.restoreState(state)
        theme_name = _normalize_theme(self.settings.theme())
        try:
            self.settings.set_theme(theme_name)
        except Exception:
            pass
        # Apply the new style for the normalized theme
        apply_theme_new(QApplication.instance(), _modern_key(theme_name))
        apply_stylesheet_new(QApplication.instance(), _modern_key(theme_name))
        # Ensure icon provider mode matches current theme
        self._apply_icon_mode_for_theme(theme_name)
        # Editors use syntax palette by normalized name
        self.tab_manager.set_theme(theme_name)

        # Hide menubar so only toolbar dropdowns are visible
        try:
            self.menuBar().setNativeMenuBar(False)
            self.menuBar().setVisible(False)
        except Exception:
            pass

        # Initialize workspace root
        if initial_root:
            d = str(initial_root)
            self.file_explorer.set_root_path(d)
            # Propagate workspace to terminal, Eve panel, and Search panel
            self.terminal.set_cwd(d)
            self.eve_panel.set_workspace_root(d)
            self.search_panel.set_root(d)
            # Optionally persist
            try:
                self.settings.set_last_project(d)
            except Exception:
                pass
        else:
            # Restore last project
            last = self.settings.last_project()
            if last:
                self.file_explorer.set_root_path(last)
                # Propagate workspace to terminal, Eve panel, and Search panel
                self.terminal.set_cwd(last)
                self.eve_panel.set_workspace_root(last)
                self.search_panel.set_root(last)

        # Finalize: in test mode, ensure port attribute is set from handshake immediately
        try:
            if os.environ.get('EVE_AUTOCOMPLETE_TEST') and getattr(self, 'auto_completion_port', 0) <= 0:
                for _path in (primary_info, fallback_info):
                    try:
                        if _path.exists():
                            with open(_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            p = int((data.get('port') or 0))
                            if p > 0:
                                self.auto_completion_port = p
                                break
                    except Exception:
                        pass
        except Exception:
            pass
    def _install_find_actions(self) -> None:
        # Find in current file (Cmd/Ctrl+F)
        self.find_in_file_action = QAction('Find', self)
        try:
            self.find_in_file_action.setShortcut(QKeySequence.StandardKey.Find)
        except Exception:
            self.find_in_file_action.setShortcut(QKeySequence('Ctrl+F'))
        self.find_in_file_action.triggered.connect(self._action_find_in_file)
        self.addAction(self.find_in_file_action)

        # Replace in file (Cmd/Ctrl+H)
        self.replace_action = QAction('Replace', self)
        try:
            self.replace_action.setShortcut(QKeySequence.StandardKey.Replace)
        except Exception:
            self.replace_action.setShortcut(QKeySequence('Ctrl+H'))
        self.replace_action.triggered.connect(self._action_replace_in_file)
        self.addAction(self.replace_action)

        # Find in files (workspace-wide) (Ctrl/Cmd+Shift+F)
        self.find_in_files_action = QAction('Find in Files', self)
        try:
            self.find_in_files_action.setShortcuts([QKeySequence('Ctrl+Shift+F'), QKeySequence('Meta+Shift+F')])
        except Exception:
            self.find_in_files_action.setShortcut(QKeySequence('Ctrl+Shift+F'))
        self.find_in_files_action.triggered.connect(self._action_find_in_files)
        self.addAction(self.find_in_files_action)

    def _action_find_in_file(self):
        ed = self._current_editor()
        if isinstance(ed, CodeEditor):
            ed.show_find_bar()
            # Seed find text from current selection if present
            try:
                sel = ed.textCursor().selectedText() or ''
                if sel:
                    ed.set_find_text(sel)
            except Exception:
                pass
            ed.setFocus()

    def _action_replace_in_file(self):
        ed = self._current_editor()
        if not isinstance(ed, CodeEditor):
            return
        ed.show_find_bar()
        # Propose current selection as default find text
        try:
            sel = ed.textCursor().selectedText() or ''
        except Exception:
            sel = ''
        find_text, ok = QInputDialog.getText(self, 'Replace', 'Find:', text=sel)
        if not ok or not (find_text or '').strip():
            ed.setFocus()
            return
        ed.set_find_text(find_text)
        repl_text, ok = QInputDialog.getText(self, 'Replace', 'Replace with:', text='')
        if not ok:
            ed.setFocus()
            return
        ed.set_replace_text(repl_text)
        # Ask whether to replace one or all
        box = QMessageBox(self)
        box.setWindowTitle('Replace')
        box.setText(f"Replace occurrences of '{find_text}' with '{repl_text}'?")
        btn_next = box.addButton('Replace Next', QMessageBox.AcceptRole)
        btn_all = box.addButton('Replace All', QMessageBox.ActionRole)
        btn_cancel = box.addButton(QMessageBox.Cancel)
        box.exec()
        if box.clickedButton() is btn_all:
            try:
                cnt = ed.replace_all()
                try:
                    self.statusBar().showMessage(f'Replaced {cnt} occurrence(s)')
                except Exception:
                    pass
            except Exception:
                pass
        elif box.clickedButton() is btn_next:
            try:
                ed.replace_one()
            except Exception:
                pass
        # Focus editor after operation
        ed.setFocus()

    def _action_find_in_files(self):
        # Switch to Search tab and focus query input
        try:
            idx = self.bottom_tabs.indexOf(self.search_panel)
            if idx != -1:
                self.bottom_tabs.setCurrentIndex(idx)
                self.search_panel.query.setFocus()
        except Exception:
            pass

    def _open_location_from_search(self, file_path: str, line: int, col: int):
        try:
            ed = self.tab_manager.open_file(Path(file_path), self.auto_completion_port, file_path=file_path)
            # Jump to line/column (1-based -> 0-based index)
            doc = ed.document()
            block = doc.findBlockByNumber(max(0, int(line) - 1))
            pos = block.position() + max(0, int(col) - 1)
            cur = ed.textCursor()
            cur.setPosition(pos)
            ed.setTextCursor(cur)
            ed.centerCursor()
            ed.setFocus()
        except Exception:
            pass

    def _current_editor(self) -> CodeEditor | None:
        w = self.tab_manager.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def _register_editor(self, editor: CodeEditor):
        try:
            if hasattr(editor, 'selectionChanged'):
                editor.selectionChanged.connect(lambda e=editor: self._update_eve_context(e))
        except Exception:
            pass
        # Push initial context
        self._update_eve_context(editor)

    def _on_tab_changed(self, _idx: int):
        ed = self._current_editor()
        if ed is not None:
            self._register_editor(ed)

    def _update_eve_context(self, editor: CodeEditor):
        try:
            file_path = str(editor.path) if editor.path else 'Untitled'
            sel = ''
            try:
                sel = editor.textCursor().selectedText() or ''
            except Exception:
                sel = ''
            # Limit selection preview
            if len(sel) > 256:
                sel = sel[:256] + '…'
            if hasattr(self.eve_panel, 'set_active_context'):
                self.eve_panel.set_active_context(file_path=file_path, selection=sel)
            else:
                # Fallback: append a status line
                try:
                    self.eve_panel.append(f'System: Active file {file_path}')
                except Exception:
                    pass
        except Exception:
            pass

    def _build_menu_bar(self) -> None:
        mb = self.menuBar()
        file_menu = mb.addMenu('&File')

        act_open_file = QAction('Open File', self)
        act_open_file.setShortcut('Ctrl+P')
        act_open_file.triggered.connect(self._open_file)

        act_open_folder = QAction('Open Folder', self)
        act_open_folder.setShortcut('Ctrl+O')
        act_open_folder.triggered.connect(self._open_folder)

        act_new_window = QAction('New Window', self)
        try:
            act_new_window.setShortcut('Ctrl+Shift+N')
        except Exception:
            pass
        act_new_window.triggered.connect(self._open_new_window)

        file_menu.addAction(act_open_file)
        file_menu.addAction(act_open_folder)
        file_menu.addSeparator()
        file_menu.addAction(act_new_window)

    def _set_toolbar_icons(self, tb: QToolBar) -> None:
        # Obtain or create an EveIconProvider so toolbar can use themed icons (used for other parts too)
        provider = getattr(self.file_explorer, 'icon_provider', None)
        if not isinstance(provider, EveIconProvider):
            provider = EveIconProvider('dark')
            # Attach to file explorer for consistency
            self.file_explorer.icon_provider = provider
            if hasattr(self.file_explorer, 'model') and hasattr(self.file_explorer.model, 'setIconProvider'):
                self.file_explorer.model.setIconProvider(provider)

        # Actions used in menus
        open_folder = QAction('Open Folder', self)
        open_file = QAction('Open File', self)
        new_window_act = QAction('New Window', self)
        theme_act_toggle = QAction('Toggle Theme', self)  # retained for menu compatibility if needed

        # Hidden Save action (not on toolbar) with standard shortcut
        save_act = QAction('Save', self)
        save_act.setObjectName('action_save')
        self.save_action = save_act
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self._save_current)
        # Add to window so shortcut is active, but keep off the toolbar
        self.addAction(save_act)

        # Wire actions
        open_folder.triggered.connect(self._open_folder)
        open_file.triggered.connect(self._open_file)
        new_window_act.triggered.connect(self._open_new_window)
        theme_act_toggle.triggered.connect(self._toggle_theme)

        # Toolbar now shows only two dropdowns: File and Theme
        # File dropdown
        file_btn = QToolButton(self)
        file_btn.setText('File')
        try:
            file_btn.setPopupMode(QToolButton.InstantPopup)
        except Exception:
            pass
        file_menu = QMenu(file_btn)
        file_menu.addAction(open_file)
        file_menu.addAction(open_folder)
        file_menu.addSeparator()
        file_menu.addAction(new_window_act)
        file_btn.setMenu(file_menu)
        tb.addWidget(file_btn)

        # Theme dropdown
        theme_btn = QToolButton(self)
        theme_btn.setText('Theme')
        try:
            theme_btn.setPopupMode(QToolButton.InstantPopup)
        except Exception:
            pass
        theme_menu = QMenu(theme_btn)
        # Only Eve, Dragon, Light
        for theme_name, label in [('eve', 'Eve'), ('dragon', 'Dragon'), ('light', 'Light')]:
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, tn=theme_name: self._apply_theme_name(tn))
            theme_menu.addAction(act)
        theme_btn.setMenu(theme_menu)
        tb.addWidget(theme_btn)

    def _apply_theme_name(self, theme_name: str) -> None:
        # Apply new style for the chosen theme and update persisted setting
        norm = _normalize_theme(theme_name)
        self.settings.set_theme(norm)
        apply_theme_new(self.app(), _modern_key(norm))
        apply_stylesheet_new(self.app(), _modern_key(norm))
        # Update icon provider mode (retain the same instance)
        provider = getattr(self.file_explorer, 'icon_provider', None)
        new_mode = _mode_for_theme(norm)
        if isinstance(provider, EveIconProvider):
            provider.set_mode(new_mode)
            self.file_explorer.model.setIconProvider(provider)
        else:
            self.file_explorer.icon_provider = EveIconProvider(new_mode)
            self.file_explorer.model.setIconProvider(self.file_explorer.icon_provider)
        # Propagate theme to editors for syntax highlighting by normalized name
        self.tab_manager.set_theme(norm)

    def _toggle_theme(self):
        # Flip based on current provider mode to guarantee a light/dark change
        provider = getattr(self.file_explorer, 'icon_provider', None)
        prev_mode = getattr(provider, 'mode', 'dark')
        current = _normalize_theme(self.settings.theme())
        # Compute new mode and target theme (flip between dragon and light)
        new_mode = 'light' if prev_mode == 'dark' else 'dark'
        nxt_theme = 'light' if new_mode == 'light' else 'dragon'
        # Apply theme and update persisted setting
        self.settings.set_theme(nxt_theme)
        apply_theme_new(self.app(), _modern_key(nxt_theme))
        apply_stylesheet_new(self.app(), _modern_key(nxt_theme))
        # Update icon provider mode (retain the same instance)
        if isinstance(provider, EveIconProvider):
            provider.set_mode(new_mode)
            self.file_explorer.model.setIconProvider(provider)
        else:
            self.file_explorer.icon_provider = EveIconProvider(new_mode)
            self.file_explorer.model.setIconProvider(self.file_explorer.icon_provider)
        # Propagate theme to editors for syntax highlighting
        self.tab_manager.set_theme(nxt_theme)

    def _apply_icon_mode_for_theme(self, theme_name: str):
        mode = _mode_for_theme(theme_name)
        provider = getattr(self.file_explorer, 'icon_provider', None)
        # Update the FileExplorer's own icon provider reference and in the model
        if isinstance(provider, EveIconProvider):
            provider.set_mode(mode)
            # Ensure the model keeps using the same provider instance
            self.file_explorer.model.setIconProvider(provider)
        else:
            self.file_explorer.icon_provider = EveIconProvider(mode)
            self.file_explorer.model.setIconProvider(self.file_explorer.icon_provider)

    def app(self):
        return QApplication.instance()

    # Legacy: kept for compatibility in case external code calls it; now delegates to same-window behavior
    def _choose_folder(self):
        self._open_folder()

    def _open_folder(self):
        d = QFileDialog.getExistingDirectory(self, 'Open Folder')
        if d:
            # Change root in the current window and propagate to panels
            self.file_explorer.set_root_path(d)
            self.terminal.set_cwd(d)
            self.eve_panel.set_workspace_root(d)
            self.search_panel.set_root(d)
            # Persist selection
            try:
                self.settings.set_last_project(d)
            except Exception:
                pass

    def _open_folder_new_window(self):
        d = QFileDialog.getExistingDirectory(self, 'Open Folder')
        if d:
            # Spawn a new main window initialized to this folder
            self._spawn_window_with_root(d)

    def _open_new_window(self):
        # Spawn a new empty main window
        app = QApplication.instance()
        new = MainWindow()
        new.show()
        self._register_window(app, new)

    def _spawn_window_with_root(self, root_path: str):
        app = QApplication.instance()
        new = MainWindow(initial_root=root_path)
        new.show()
        self._register_window(app, new)

    @staticmethod
    def _register_window(app: QApplication, win: 'MainWindow') -> None:
        # Keep a reference on the QApplication instance to prevent GC
        try:
            registry = getattr(app, '_eve_windows', None)
            if registry is None:
                registry = []
            registry.append(win)
            setattr(app, '_eve_windows', registry)
        except Exception:
            pass

    def _open_file(self):
        p, _ = QFileDialog.getOpenFileName(self, 'Open File')
        if p:
            self._open_file_path(p)

    def _open_file_path(self, p: str):
        # Give the process id to the tab manager to open the file
        self.tab_manager.open_file(Path(p), self.auto_completion_port, file_path=p)

    def _save_current(self):
        if not self.tab_manager.save_current():
            QMessageBox.information(self, 'Save', 'Nothing to save.')

    def _run_health(self):
        # Prefer selected project, else repo root
        proj = self.settings.last_project() or str(Path(__file__).resolve().parents[2])
        self.terminal.run_health(proj)

    def _new_project(self):
        dlg = NewProjectDialog(self)
        if dlg.exec() == dlg.Accepted:
            dest = dlg.result_path()
            if not dest:
                QMessageBox.warning(self, 'New Project', 'Please provide name and location.')
                return
            if dest.exists():
                QMessageBox.warning(self, 'New Project', 'Destination already exists.')
                return
            ok = NewProjectDialog.create_basic_project(dest)
            if ok:
                # Open newly created project in a new window
                self._spawn_window_with_root(str(dest))
                try:
                    self.settings.set_last_project(str(dest))
                except Exception:
                    pass
            else:
                QMessageBox.critical(self, 'New Project', 'Failed to create project.')

    def _on_context_size(self, size: int) -> None:
        try:
            self.context_indicator.setText(f"Context: {size:,}")
        except Exception:
            # Fallback without thousands separator
            self.context_indicator.setText(f"Context: {size}")

    def closeEvent(self, e):
        # Dispose editors to stop timers and background work before shutdown
        try:
            if hasattr(self, 'tab_manager') and hasattr(self.tab_manager, 'dispose_all_editors'):
                self.tab_manager.dispose_all_editors()
        except Exception:
            pass

        # Stop autocomplete polling timer explicitly (paranoid but clear)
        try:
            if hasattr(self, '_ac_timer') and self._ac_timer is not None:
                if self._ac_timer.isActive():
                    self._ac_timer.stop()
                self._ac_timer.deleteLater()
        except Exception:
            pass

        # Unregister this window and terminate autocomplete server only if this is the last window
        try:
            from PySide6.QtWidgets import QApplication
            import os, signal
            app = QApplication.instance()
            registry = getattr(app, '_eve_windows', []) if app else []
            # Remove this window from the registry if present
            try:
                if registry:
                    try:
                        registry.remove(self)
                    except ValueError:
                        pass
                    setattr(app, '_eve_windows', registry)
            except Exception:
                pass
            is_last = (not registry) or (len(registry) <= 0)
            if is_last and getattr(self, 'auto_completion_pid', 0):
                os.kill(self.auto_completion_pid, signal.SIGTERM)
        except Exception:
            pass

        # Persist window state
        try:
            self.settings.save_geometry(self.saveGeometry(), self.saveState())
        except Exception:
            pass

        super().closeEvent(e)