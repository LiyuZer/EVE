from __future__ import annotations
from pathlib import Path
import sys
import os
import signal
import shutil
import getpass
import socket
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtCore import QProcess, QByteArray, Signal, Qt
from PySide6.QtGui import QTextCursor, QPalette, QColor

from src.eve_session import EveSession  # added: session support


def choose_shell() -> tuple[str, list[str]]:
    """Choose an interactive shell appropriate for the platform.
    - POSIX: prefer $SHELL if executable; else zsh, then bash, then sh (all with -i)
    - Windows: prefer powershell (or pwsh), else cmd (no args)
    """
    if sys.platform.startswith('win'):
        for name in ('powershell', 'pwsh', 'powershell.exe'):
            path = shutil.which(name)
            if path:
                return path, []
        path = shutil.which('cmd') or shutil.which('cmd.exe') or 'cmd.exe'
        return path, []
    # POSIX
    env_shell = os.environ.get('SHELL')
    if env_shell and os.path.isfile(env_shell) and os.access(env_shell, os.X_OK):
        return env_shell, ['-i']
    for name in ('zsh', 'bash', 'sh'):
        path = shutil.which(name)
        if path:
            return path, ['-i']
    # Fallback
    return '/bin/sh', ['-i']


def handle_cd(current_base: Path, command: str) -> tuple[bool, Path, str, str]:
    """Pure helper for handling cd commands.
    Returns (handled, new_cwd, to_send, message)
    - If handled and directory exists: new_cwd updated, to_send is cd 'path' (quoted), message notes cwd set
    - If handled but dir missing: cwd unchanged, to_send '', message notes error
    - If not a cd command: handled False, returns passthrough
    """
    s = (command or '').strip()
    if s == 'cd' or s.startswith('cd '):
        arg = s[2:].strip()
        base = current_base
        if arg in ('', '~'):
            target = Path(os.path.expanduser('~'))
        else:
            p = Path(arg)
            target = (base / p).resolve() if not p.is_absolute() else p.resolve()
        if target.exists() and target.is_dir():
            # Quote appropriately for platform
            if sys.platform.startswith('win'):
                quoted = f'"{str(target)}"'
            else:
                quoted = f"'{str(target)}'"
            return True, target, f"cd {quoted}", f"[cwd set to] {target}"
        else:
            return True, base, '', f"cd: no such file or directory: {arg}"
    return False, current_base, command, ''


class TerminalEdit(QPlainTextEdit):
    """Inline terminal editor: displays output and lets the user type at the end.
    - Prevents editing prior output (history) using a prompt boundary index
    - Emits commandSubmitted when user presses Enter
    - Keeps a simple history navigated by Up/Down arrows
    - Supports setting colors via set_colors
    """

    commandSubmitted = Signal(str)
    interruptRequested = Signal()
    completionRequested = Signal(str)
    clearRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setReadOnly(False)
        self._prompt_pos: int = 0
        self._history: list[str] = []
        self._hist_index: int = -1  # points just after last entry when == len(history)
        # Start with an empty document; let the user type immediately on the first line
        self._prompt_pos = len(self.toPlainText())

    def append_output(self, text: str) -> None:
        # Always append at end, update prompt boundary afterwards
        tc = self.textCursor()
        tc.movePosition(QTextCursor.End)
        self.setTextCursor(tc)
        if text:
            self.insertPlainText(text)
        # Ensure we end with a newline to start a fresh prompt line
        doc = self.toPlainText()
        if not doc.endswith("\n"):
            self.insertPlainText("\n")
        # New prompt boundary is the end of document
        self._prompt_pos = len(self.toPlainText())
        # Move cursor to end for typing
        tc.movePosition(QTextCursor.End)
        self.setTextCursor(tc)

    def insert_prompt(self, prompt_text: str) -> None:
        """Insert a visible prompt at the end and set the input boundary after it."""
        tc = self.textCursor()
        tc.movePosition(QTextCursor.End)
        self.setTextCursor(tc)
        if prompt_text:
            self.insertPlainText(prompt_text)
        self._prompt_pos = len(self.toPlainText())
        tc.movePosition(QTextCursor.End)
        self.setTextCursor(tc)

    def set_colors(self, fg_hex: str, bg_hex: str) -> None:
        # Apply both palette and stylesheet to ensure visibility across styles
        pal = self.palette()
        fg = QColor(fg_hex)
        bg = QColor(bg_hex)
        pal.setColor(QPalette.Text, fg)
        pal.setColor(QPalette.Base, bg)
        pal.setColor(QPalette.WindowText, fg)
        pal.setColor(QPalette.Window, bg)
        self.setPalette(pal)
        # style sheet for robustness and selection color
        try:
            self.setStyleSheet(
                f"QPlainTextEdit {{ color: {fg_hex}; background-color: {bg_hex}; selection-background-color: {fg_hex}22; }}"
            )
        except Exception:
            pass

    def current_input_text(self) -> str:
        doc = self.toPlainText()
        return doc[self._prompt_pos:].rstrip('\n')

    def _set_current_input_text(self, s: str) -> None:
        tc = self.textCursor()
        tc.movePosition(QTextCursor.End)
        self.setTextCursor(tc)
        # Select from prompt to end
        tc.setPosition(self._prompt_pos)
        end_pos = len(self.toPlainText())
        tc.setPosition(end_pos, QTextCursor.KeepAnchor)
        self.setTextCursor(tc)
        tc.removeSelectedText()
        tc.insertText(s)
        self.setTextCursor(tc)

    def keyPressEvent(self, event):  # type: ignore[override]
        key = event.key()
        tc = self.textCursor()

        # Ctrl-C -> request interrupt (like terminal)
        if key == Qt.Key_C and (event.modifiers() & Qt.ControlModifier):
            self.interruptRequested.emit()
            return

        # Ctrl-L -> clear screen
        if key == Qt.Key_L and (event.modifiers() & Qt.ControlModifier):
            self.clearRequested.emit()
            return

        # Tab -> request completion from parent
        if key == Qt.Key_Tab:
            self.completionRequested.emit(self.current_input_text())
            return

        if key in (Qt.Key_Return, Qt.Key_Enter):
            cmd = self.current_input_text()
            # Finish the line visually
            tc.movePosition(QTextCursor.End)
            self.setTextCursor(tc)
            self.insertPlainText("\n")
            # update prompt boundary for next input
            self._prompt_pos = len(self.toPlainText())
            # manage history
            if cmd.strip():
                self._history.append(cmd)
            self._hist_index = len(self._history)
            # emit after updating UI
            self.commandSubmitted.emit(cmd)
            return

        if key == Qt.Key_Backspace:
            # Disallow backspace if at boundary or earlier
            if tc.position() <= self._prompt_pos:
                return
            # else let it backspace normally
            return super().keyPressEvent(event)

        if key == Qt.Key_Left:
            # Disallow moving cursor left into history
            if tc.position() <= self._prompt_pos:
                return
            return super().keyPressEvent(event)

        if key == Qt.Key_Home:
            # Jump to prompt start, not document start
            tc.setPosition(self._prompt_pos)
            self.setTextCursor(tc)
            return

        if key == Qt.Key_Up:
            if self._history:
                if self._hist_index > 0:
                    self._hist_index -= 1
                elif self._hist_index == -1:
                    self._hist_index = len(self._history) - 1
                self._set_current_input_text(self._history[self._hist_index])
            return

        if key == Qt.Key_Down:
            if self._history:
                if self._hist_index < len(self._history) - 1:
                    self._hist_index += 1
                    self._set_current_input_text(self._hist_index < len(self._history) and self._history[self._hist_index] or "")
                else:
                    # Move to empty entry after the last command
                    self._hist_index = len(self._history)
                    self._set_current_input_text("")
            return

        # Prevent any selection edits that cross into history
        if event.text():
            # If there's a selection starting before prompt, clamp it
            sel_start = min(tc.selectionStart(), tc.selectionEnd()) if tc.hasSelection() else tc.position()
            if sel_start < self._prompt_pos:
                # Move cursor to end (prompt) before inserting
                tc.setPosition(len(self.toPlainText()))
                self.setTextCursor(tc)
        return super().keyPressEvent(event)


class TerminalWidget(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # One process used per-command now (not persistent interactive shell)
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._read_stdout)
        self.proc.readyReadStandardError.connect(self._read_stderr)
        self.proc.finished.connect(self._on_finished)

        # Eve session management (.eve/session.sh)
        # Use a stable, explicit repo_root based on IDE code location
        repo_root = Path(__file__).resolve().parents[2]
        self.session = EveSession(repo_root=repo_root)
        # Ensure session exists but do not reset cwd; preserve across widget restarts
        try:
            self.session.ensure(reset=False)
        except Exception:
            pass

        # Current working directory mirror (from session)
        try:
            self.cwd: Path | None = self.session.current_cwd()
        except Exception:
            self.cwd = None

        # Inline terminal editor instead of a separate input widget
        self.terminal = TerminalEdit(self)
        self.terminal.commandSubmitted.connect(self._on_submit_command)
        self.terminal.interruptRequested.connect(self.stop)
        self.terminal.completionRequested.connect(self._on_tab_complete)
        self.terminal.clearRequested.connect(self.clear_screen)
        # Back-compat alias so callers/tests can use term.output
        self.output = self.terminal
        # Apply Dracula dark colors by default; allow env overrides
        fg = os.getenv('EVE_TERMINAL_FG', '#f8f8f2')
        bg = os.getenv('EVE_TERMINAL_BG', '#282a36')
        try:
            self.terminal.set_colors(fg, bg)
        except Exception:
            pass

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.terminal)

        # Show initial prompt
        try:
            self._show_prompt()
        except Exception:
            pass

    def _venv_prefix(self) -> str:
        try:
            v = self.session.current_venv()
        except Exception:
            v = None
        if v:
            name = v.name or 'venv'
            return f"({name}) "
        return ""

    def _prompt_str(self) -> str:
        user = getpass.getuser()
        host = socket.gethostname().split('.')[0]
        # Determine a friendly cwd (use ~ for home)
        try:
            cwd = self.cwd or self._initial_workdir()
        except Exception:
            cwd = self._initial_workdir()
        home = Path(os.path.expanduser('~'))
        try:
            disp = str(cwd)
            if cwd == home or str(cwd).startswith(str(home) + os.sep):
                try:
                    disp = '~' + str(cwd)[len(str(home)):] if cwd != home else '~'
                except Exception:
                    disp = '~'
        except Exception:
            disp = str(cwd)
        # Use $ prompt (even on Windows for consistency)
        return f"{self._venv_prefix()}{user}@{host}:{disp}$ "

    def _show_prompt(self) -> None:
        self.terminal.insert_prompt(self._prompt_str())
    def append(self, text: str):
        self.terminal.append_output(text)

    def clear_screen(self) -> None:
        try:
            self.terminal.setPlainText("")
            # Reset boundary and show prompt
            self.terminal._prompt_pos = 0
            self._show_prompt()
        except Exception:
            pass

    def _read_stdout(self):
        data: QByteArray = self.proc.readAllStandardOutput()
        self.terminal.append_output(bytes(data).decode('utf-8', errors='replace'))

    def _read_stderr(self):
        data: QByteArray = self.proc.readAllStandardError()
        self.terminal.append_output(bytes(data).decode('utf-8', errors='replace'))

    def _on_finished(self, code: int, _status):
        # Do not print exit status; just show prompt
        try:
            self._show_prompt()
        except Exception:
            pass

    def set_cwd(self, path: str | Path, stop_running: bool = True) -> None:
        """Set the default working directory for terminal runs.
        If a process is running and stop_running=True, stop it before switching.
        Persist into session as well.
        """
        try:
            new_path = Path(path).resolve()
        except Exception:
            return
        if stop_running and self.proc.state() != QProcess.NotRunning:
            self.stop()
        # Persist via EveSession; allow outside-workspace when explicitly requested via UI
        old_restrict = getattr(self.session, "restrict_cwd_to_repo", True)
        try:
            self.session.restrict_cwd_to_repo = False
            ok, msg = self.session.update_cd(str(new_path))
        finally:
            try:
                self.session.restrict_cwd_to_repo = old_restrict
            except Exception:
                pass
        if ok:
            self.cwd = new_path
        if msg:
            self.append(msg)
        # Update the prompt to reflect new cwd
        try:
            self._show_prompt()
        except Exception:
            pass

    def _resolve_repo_root(self, start: Path) -> Path:
        # Walk upwards from start to find a directory containing main.py
        cur = start.resolve()
        if cur.is_file():
            cur = cur.parent
        for _ in range(10):  # search several levels up
            if (cur / 'main.py').exists():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
        # Fallback: repo root relative to this file
        return Path(__file__).resolve().parents[2]

    def _initial_workdir(self) -> Path:
        # Prefer widget cwd; else session cwd; else repo root near this file
        try:
            if self.cwd:
                return self.cwd
        except Exception:
            pass
        try:
            sess_cwd = self.session.current_cwd()
            if sess_cwd:
                return sess_cwd
        except Exception:
            pass
        start = self.cwd or Path(__file__).resolve().parents[2]
        return self._resolve_repo_root(start)

    def _handle_cd(self, command: str) -> tuple[bool, str]:
        """Handle cd commands by persisting in EveSession and updating self.cwd."""
        base = self.cwd or self._initial_workdir()
        handled, new_cwd, _to_send, message = handle_cd(base, command)
        if handled:
            if new_cwd != base and new_cwd.exists() and new_cwd.is_dir():
                # Persist change into session file
                ok, msg = self.session.update_cd(str(new_cwd))
                if ok:
                    self.cwd = new_cwd
                # Prefer session message if available, else fall back to local
                if msg:
                    message = msg
            if message:
                self.append(message)
            try:
                self._show_prompt()
            except Exception:
                pass
            return True, ''
        return False, command

    def _handle_export_unset(self, command: str) -> tuple[bool, str]:
        """Intercept simple 'export NAME=VALUE' and 'unset NAME' to persist in session."""
        s = (command or '').strip()
        if not s:
            return False, command
        if s.startswith('export '):
            # Very simple parse: export NAME=VALUE (no complex expansions)
            rest = s[len('export '):].strip()
            if '=' in rest:
                name, value = rest.split('=', 1)
                name = name.strip()
                value = value.strip().strip('\"').strip("'")
                ok, msg = self.session.export(name, value)
                self.append(msg)
                try:
                    self._show_prompt()
                except Exception:
                    pass
                return True, '' if ok else ''
            return False, command
        if s.startswith('unset '):
            name = s[len('unset '):].strip()
            ok, msg = self.session.unset(name)
            self.append(msg)
            try:
                self._show_prompt()
            except Exception:
                pass
            return True, '' if ok else ''
        return False, command

    def _handle_clear(self, command: str) -> tuple[bool, str]:
        s = (command or '').strip()
        if s == 'clear':
            self.clear_screen()
            return True, ''
        return False, command

    def _handle_venv(self, command: str) -> tuple[bool, str]:
        """Intercept common venv activation/deactivation commands to persist in session.
        - Handles: 'source X/bin/activate', '. X/bin/activate', and 'deactivate'.
        """
        s = (command or '').strip()
        if not s:
            return False, command
        lower = s.lower()
        # Deactivate
        if lower == 'deactivate':
            ok, msg = self.session.deactivate_venv()
            self.append(msg)
            try:
                self._show_prompt()
            except Exception:
                pass
            return True, ''
        # Activate: source or dot
        if lower.startswith('source ') or lower.startswith('. '):
            # Extract path part after the command keyword
            try:
                parts = s.split(None, 1)
                if len(parts) < 2:
                    return False, command
                path_str = parts[1].strip()
                if (path_str.startswith("'") and path_str.endswith("'")) or (path_str.startswith('"') and path_str.endswith('"')):
                    path_str = path_str[1:-1]
                p = Path(path_str)
                base = self.cwd or self._initial_workdir()
                act_path = (base / p).resolve() if not p.is_absolute() else p.resolve()
                # Expect .../bin/activate or .../Scripts/activate
                if act_path.name.startswith('activate'):
                    bin_dir = act_path.parent
                    venv_root = bin_dir.parent
                    ok, msg = self.session.activate_venv(venv_root)
                    self.append(msg)
                    try:
                        self._show_prompt()
                    except Exception:
                        pass
                    return True, ''
            except Exception:
                return False, command
        return False, command

    def _compose_run_program(self, command: str) -> tuple[str, list[str]]:
        """Build a one-shot shell invocation to source session then run command."""
        if sys.platform.startswith('win'):
            # Minimal Windows support: run in cmd; session file is POSIX so we skip sourcing.
            prog = shutil.which('cmd') or shutil.which('cmd.exe') or 'cmd.exe'
            return prog, ['/d', '/s', '/c', command]
        # POSIX: use /bin/sh -lc "<src>; <cmd>"
        sh = shutil.which('sh') or '/bin/sh'
        src = self.session.source_command()
        payload = f"{src}; {command}"
        return sh, ['-lc', payload]

    def _on_submit_command(self, cmd: str) -> None:
        if not cmd:
            return
        # Avoid starting a new command while one is running
        if self.proc.state() != QProcess.NotRunning:
            self.append('[process already running; stop or wait]')
            return

        # Intercept persistence commands first
        handled, rewritten = self._handle_clear(cmd)
        if handled:
            return
        handled, rewritten = self._handle_cd(cmd)
        if handled:
            return
        handled, rewritten = self._handle_export_unset(cmd)
        if handled:
            return
        handled, rewritten = self._handle_venv(cmd)
        if handled:
            return

        to_run = rewritten if rewritten else cmd
        if to_run:
            try:
                program, args = self._compose_run_program(to_run)
                self.proc.setProgram(program)
                self.proc.setArguments(args)
                # Working directory: prefer stable widget cwd, then session cwd
                workdir = self._initial_workdir()
                self.proc.setWorkingDirectory(str(workdir))
                self.proc.start()
            except Exception:
                pass

    # Backwards-compatible helper if callers want to run a command string
    def run_command(self, cmd: str) -> None:
        self._on_submit_command(cmd)

    def run_health(self, project_root: str | Path | None = None):
        if self.proc.state() != QProcess.NotRunning:
            # A command is active; avoid clobbering it
            self.append('[healthcheck skipped: terminal session running]')
            return
        # Prefer explicit project_root, but resolve to repo containing main.py
        if project_root:
            repo = self._resolve_repo_root(Path(project_root))
        else:
            try:
                repo = self._resolve_repo_root(self.session.current_cwd())
            except Exception:
                repo = self._resolve_repo_root(Path(__file__).resolve().parents[2])
        self.append(f"Running healthcheck in: {repo}")
        # Prefer venv python if active
        py_path: str | None = None
        try:
            v = self.session.current_venv()
            if v:
                cand = v / ('Scripts' if sys.platform.startswith('win') else 'bin')
                for nm in (['python.exe', 'python'] if sys.platform.startswith('win') else ['python', 'python3']):
                    p = cand / nm
                    if p.exists():
                        py_path = str(p)
                        break
        except Exception:
            pass
        program = py_path or sys.executable
        self.proc.setProgram(program)
        self.proc.setArguments(['-u', 'main.py', '--health'])
        self.proc.setWorkingDirectory(str(repo))
        self.proc.start()

    def stop(self):
        # If no process, behave like terminal: clear current input, print ^C, show prompt
        if self.proc.state() == QProcess.NotRunning:
            try:
                self.terminal._set_current_input_text("")
            except Exception:
                pass
            try:
                self.append('^C')
                self._show_prompt()
            except Exception:
                pass
            return
        # Otherwise interrupt running process
        try:
            self.append('^C')
        except Exception:
            pass
        if self.proc.state() != QProcess.NotRunning:
            # Try gentle interrupt on POSIX, else kill
            if not sys.platform.startswith('win'):
                try:
                    pid = int(self.proc.processId())  # type: ignore[attr-defined]
                    if pid > 0:
                        os.kill(pid, signal.SIGINT)
                except Exception:
                    pass
            # If still running, kill
            if self.proc.state() != QProcess.NotRunning:
                self.proc.kill()
                self.proc.waitForFinished(2000)

    # ---------------- Tab completion ----------------
    def _split_last_token(self, s: str) -> tuple[str, str]:
        # Return (prefix_with_space, last_token)
        if not s:
            return "", ""
        i_space = max(s.rfind(' '), s.rfind('\t'))
        if i_space == -1:
            return "", s
        return s[: i_space + 1], s[i_space + 1 :]

    def _effective_path_dirs(self) -> list[Path]:
        dirs: list[Path] = []
        # Active venv bin/Scripts first
        try:
            v = self.session.current_venv()
        except Exception:
            v = None
        if v:
            vbin = v / ('Scripts' if sys.platform.startswith('win') else 'bin')
            if vbin.exists():
                dirs.append(vbin)
        # Then system PATH
        for part in os.environ.get('PATH', '').split(os.pathsep):
            if not part:
                continue
            p = Path(part).expanduser()
            if p.exists() and p.is_dir():
                dirs.append(p)
        return dirs

    def _is_executable(self, p: Path) -> bool:
        if not p.exists() or not p.is_file():
            return False
        if sys.platform.startswith('win'):
            return p.suffix.lower() in ('.exe', '.bat', '.cmd', '.com') or os.access(str(p), os.X_OK)
        return os.access(str(p), os.X_OK)

    def _program_candidates(self, name_part: str) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        # Builtins first
        builtins = ['cd', 'export', 'unset', 'source', 'deactivate', 'clear']
        for b in builtins:
            if b.startswith(name_part) and b not in seen:
                seen.add(b)
                out.append(b)
        # Then PATH executables
        for d in self._effective_path_dirs():
            try:
                for child in d.iterdir():
                    nm = child.name
                    if nm.startswith(name_part) and nm not in seen and self._is_executable(child):
                        seen.add(nm)
                        out.append(nm)
            except Exception:
                continue
        out.sort()
        return out

    def _on_tab_complete(self, text: str) -> None:
        try:
            prefix, token = self._split_last_token(text)
            base = self.cwd or self._initial_workdir()
            # Expand ~ in token
            token_exp = os.path.expanduser(token)
            # Determine directory portion and name fragment
            sep_idx = max(token_exp.rfind('/'), token_exp.rfind('\\'))
            dir_part = token_exp[: sep_idx + 1] if sep_idx >= 0 else ''
            name_part = token_exp[sep_idx + 1 :] if sep_idx >= 0 else token_exp

            # If no dir separator and token is the first word, do PATH program completion
            is_first_word = (prefix.strip() == '')
            if sep_idx < 0 and is_first_word:
                names = self._program_candidates(name_part)
                if not names:
                    return
                # Single match
                if len(names) == 1:
                    completed = names[0] + ' '
                    self.terminal._set_current_input_text(completed)
                    return
                # Common prefix
                common = os.path.commonprefix(names)
                if common and len(common) > len(name_part):
                    self.terminal._set_current_input_text(common)
                    return
                # List suggestions
                self.append('  '.join(names))
                self._show_prompt()
                self.terminal._set_current_input_text(text)
                return

            # Else do filesystem completion (relative to cwd or given dir)
            # Resolve directory to search
            if dir_part:
                dir_path = Path(dir_part)
                if not dir_path.is_absolute():
                    dir_path = (base / dir_path)
            else:
                dir_path = base
            try:
                dir_path = dir_path.expanduser().resolve()
            except Exception:
                return  # invalid path
            if not dir_path.exists() or not dir_path.is_dir():
                return
            # Collect matches
            entries = []
            try:
                for child in dir_path.iterdir():
                    nm = child.name
                    if nm.startswith(name_part):
                        display = nm + ('/' if child.is_dir() else '')
                        entries.append((nm, display, child.is_dir()))
            except Exception:
                return
            if not entries:
                return
            entries.sort(key=lambda t: t[0])
            names = [e[0] for e in entries]
            # Single match -> complete inline
            if len(entries) == 1:
                display = entries[0][1]
                new_token = (dir_part or '') + display
                self.terminal._set_current_input_text(prefix + new_token)
                return
            # Multiple -> try common prefix extension
            common = os.path.commonprefix(names)
            if common and len(common) > len(name_part):
                new_token = (dir_part or '') + common
                self.terminal._set_current_input_text(prefix + new_token)
                return
            # Otherwise, list suggestions and restore prompt+input
            displays = [e[1] for e in entries]
            self.append('  '.join(displays))
            self._show_prompt()
            self.terminal._set_current_input_text(text)
        except Exception:
            # Be resilient; ignore completion errors
            pass