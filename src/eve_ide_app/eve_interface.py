from __future__ import annotations
from pathlib import Path
import sys
import re
import html as htmlmod
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit
)
from PySide6.QtCore import Qt, QProcess, QByteArray, QProcessEnvironment, Signal
from PySide6.QtGui import QPixmap


class EveInterfaceWidget(QWidget):
    # Emits the current context size (number) parsed from agent output lines
    contextSizeChanged = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Track workspace root for the agent process (IDE-selected project folder)
        self.workspace_root: Path | None = None
        # Track active editor context
        self.current_file_path: str | None = None
        self.current_selection: str = ""

        # Header with logo and title
        header = QWidget(self)
        header.setObjectName('eveHeader')
        h = QHBoxLayout(header)
        h.setContentsMargins(8, 6, 8, 6)
        logo_path = Path(__file__).resolve().parents[2] / 'eve-logo.jpg'
        if logo_path.exists():
            pix = QPixmap(str(logo_path)).scaledToHeight(20, Qt.SmoothTransformation)
            logo = QLabel()
            logo.setPixmap(pix)
            h.addWidget(logo)
        title = QLabel('Eve Interface')
        h.addWidget(title)
        h.addStretch(1)
        # Small active context indicator
        self.active_ctx_label = QLabel('Active: —')
        try:
            self.active_ctx_label.setObjectName('activeContextLabel')
        except Exception:
            pass
        h.addWidget(self.active_ctx_label)
        layout.addWidget(header)

        # Output area (rich text)
        self.output = QTextEdit(self)
        self.output.setObjectName('eveOutput')
        self.output.setReadOnly(True)
        self.output.setPlaceholderText('Eve is ready. Press Run Agent to start or type a message to chat...')
        layout.addWidget(self.output, 1)

        # Input + controls row
        inrow = QHBoxLayout()
        self.input = QLineEdit(self)
        self.input.setPlaceholderText('Type a prompt or command for Eve...')
        # Allow pressing Enter to send
        try:
            self.input.returnPressed.connect(self._on_send)
        except Exception:
            pass
        send = QPushButton('Send')
        send.clicked.connect(self._on_send)
        # Run/Stop controls
        self.run_btn = QPushButton('Run Agent', self)
        self.stop_btn = QPushButton('Stop', self)
        self.stop_btn.setEnabled(False)
        self.run_btn.clicked.connect(self.run_agent)
        self.stop_btn.clicked.connect(self.stop)

        inrow.addWidget(self.input, 1)
        inrow.addWidget(send)
        inrow.addWidget(self.run_btn)
        inrow.addWidget(self.stop_btn)
        layout.addLayout(inrow)

        # Subprocess to run the agent
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self._read_stdout)
        self.proc.readyReadStandardError.connect(self._read_stderr)
        self.proc.finished.connect(self._on_finished)

    # --------------- Public API ---------------
    def append(self, text: str):
        """Append plain text; for modern UI we wrap via formatting into HTML, but keep text visible in toPlainText."""
        self.append_html(self._format_line(text.rstrip('\n')))

    def append_html(self, html: str):
        # QTextEdit.append treats input as rich text if HTML-like tags are present
        self.output.append(html)

    def set_workspace_root(self, path: str | Path, stop_running: bool = True) -> None:
        """Set the IDE workspace root for the agent panel. If a process is running,
        stop it first (by default) to avoid cross-context output.
        """
        try:
            new_root = Path(path).resolve()
        except Exception:
            return
        if stop_running and self.proc.state() != QProcess.NotRunning:
            self.stop()
        self.workspace_root = new_root
        self.append(f'System: Workspace set to {self.workspace_root}')

    def set_active_context(self, *, file_path: str, selection: str = "") -> None:
        """Receive active editor context: current file path and selection preview.
        Stores state and updates a small header label (no chat log spam).
        """
        try:
            self.current_file_path = file_path
            self.current_selection = selection or ""
            # Update compact header label
            short = file_path if len(file_path) <= 48 else ('…' + file_path[-47:])
            try:
                self.active_ctx_label.setText(f'Active: {short}')
            except Exception:
                pass
            # Do not append a chat line about active file; keep the Eve box clean
        except Exception:
            # Non-fatal
            pass
    # --------------- QProcess wiring ---------------
    def _resolve_repo_root(self, start: Path | None = None) -> Path:
        # Walk upwards from start (or current file) to find a directory containing main.py
        cur = (start or Path(__file__).resolve().parents[2]).resolve()
        if cur.is_file():
            cur = cur.parent
        for _ in range(10):
            if (cur / 'main.py').exists():
                return cur
            if cur.parent == cur:
                break
            cur = cur.parent
        # Fallback: repo root relative to this file
        return Path(__file__).resolve().parents[2]

    def run_agent(self, project_root: str | Path | None = None):
        if self.proc.state() != QProcess.NotRunning:
            return
        # Prefer explicit project_root, else current workspace_root, else default
        start_from = Path(project_root) if project_root else (self.workspace_root or Path(__file__).resolve().parents[2])
        repo = self._resolve_repo_root(start_from)
        self.append('System: Starting agent...')
        self.proc.setProgram(sys.executable)
        self.proc.setArguments(['-u', 'main.py', '--mode', 'ide'])
        self.proc.setWorkingDirectory(str(repo))
        # Propagate workspace to the agent process via environment
        env = QProcessEnvironment.systemEnvironment()
        if self.workspace_root:
            env.insert('EVE_WORKSPACE_ROOT', str(self.workspace_root))
        self.proc.setProcessEnvironment(env)
        self.proc.start()
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop(self):
        if self.proc.state() != QProcess.NotRunning:
            self.proc.kill()
            self.proc.waitForFinished(2000)
            self.append('System: Stopped agent.')
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _on_finished(self, code: int, _status):
        self.append(f'System: Agent exited with code {code}.')
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def _process_line(self, line: str, is_error: bool = False):
        """Process a single agent output line.
        - If it contains a context size, emit the signal and suppress display in the chat box.
        - Otherwise, append formatted output (stderr lines are prefixed with 'Error: ').
        """
        s = line or ''
        # Detect and emit context size if present, but do not show in chat box
        try:
            m = re.search(r"Context Tree size:\s*(\d+)", s)
            if m:
                try:
                    self.contextSizeChanged.emit(int(m.group(1)))
                except Exception:
                    pass
                return  # suppress showing
        except Exception:
            pass

        if s.strip() == '':
            self.output.append('')
            return

        if is_error:
            self.append_html(self._format_line(f'Error: {s}'))
        else:
            self.append_html(self._format_line(s))

    def _read_stdout(self):
        data: QByteArray = self.proc.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='replace')
        for line in text.splitlines():
            self._process_line(line, is_error=False)

    def _read_stderr(self):
        data: QByteArray = self.proc.readAllStandardError()
        text = bytes(data).decode('utf-8', errors='replace')
        for line in text.splitlines():
            self._process_line(line, is_error=True)

    # --------------- Interaction ---------------
    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        # Show user's message
        self.append(f'Liyu: {text}')

        # If agent is running, forward to stdin; otherwise give a helpful hint
        if self.proc.state() != QProcess.NotRunning:
            try:
                self.proc.write((text + '\n').encode('utf-8'))
                self.proc.flush()
            except Exception:
                pass
        else:
            self.append('System: Agent is not running. Press "Run Agent" to start Eve.')

        self.input.clear()

    # --------------- Formatting ---------------
    _ansi_re = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

    def _strip_ansi(self, s: str) -> str:
        return self._ansi_re.sub('', s)

    def _format_line(self, line: str) -> str:
        """Convert a single line into styled HTML. Keep simple, deterministic rules.
        - Strip ANSI
        - Highlight prefixes: Eve:, System:, You:, Error:
        - Default: plain text wrapped in a span
        """
        raw = self._strip_ansi(line or '')
        raw = raw.rstrip('\n')
        lower = raw.lower()

        def esc(s: str) -> str:
            return htmlmod.escape(s, quote=False)

        def row(label_color: str, body_color: str, bold_label: bool = True):
            if ':' in raw:
                label, body = raw.split(':', 1)
                label += ':'
                body = body.lstrip()
            else:
                label, body = '', raw
            label_html = f'<span style="color:{label_color};{"font-weight:bold;" if bold_label else ""}' + f'">{esc(label)}</span>' if label else ''
            body_html = f'<span style="color:{body_color}">{esc(body)}</span>'
            if label_html:
                return f'<div>{label_html} {body_html}</div>'
            return f'<div>{body_html}</div>'

        # Palette (tuned to be readable on light/dark):
        YELLOW = '#F1C40F'
        MAGENTA = '#C678DD'
        RED = '#E06C75'
        GREEN = '#98C379'
        FG = '#BBBBBB'  # neutral

        if lower.startswith('eve:'):
            return row(YELLOW, FG)
        if lower.startswith('system:'):
            return row(MAGENTA, FG)
        if lower.startswith('liyu:'):
            return row(GREEN, FG)
        if lower.startswith('error:') or 'traceback' in lower or 'exception' in lower:
            # emphasize errors in red
            return row(RED, RED, bold_label=True)
        # default
        return f'<div><span style="color:{FG}">{esc(raw)}</span></div>'