from __future__ import annotations
from pathlib import Path
from typing import Optional
from src.code_indexer import CodeIndexer
from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTabWidget, QTextEdit
from PySide6.QtGui import QFont
from PySide6.QtCore import Signal, QFileSystemWatcher, QTimer

from .highlighters import create_highlighter
from .highlighting_registry import get_language_for_path
from .ac_client import resolve_port, async_post_json, sync_post_json, fallback_completion
from .cooldown import CooldownGate
import asyncio
import os

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QtCore.QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event: QtGui.QPaintEvent):  # type: ignore[override]
        try:
            self._editor._line_number_area_paint_event(event)
        except Exception:
            pass

class CodeEditor(QPlainTextEdit):
    modifiedChanged = Signal(bool)
    # Emitted when the file is reloaded from disk due to external change
    fileReloaded = Signal(str)
    # Emitted when an external change is detected (even if not reloaded due to unsaved edits)
    externalFileChanged = Signal(str)
    # Thread-safe delivery of completion text to the UI thread
    completionReady = Signal(int, str)

    def __init__(self, path: Path | None = None, parent: QWidget | None = None, auto_completion_port: int = 0, file_path: str = ""):
        super().__init__(parent)
        # Lifecycle flags
        self._alive: bool = True
        self._disposed: bool = False
        try:
            self.destroyed.connect(self._on_destroyed)
        except Exception:
            pass

        self._path: Path | None = path
        self._watcher: QFileSystemWatcher | None = None
        self._suppress_fs_events: bool = False
        self._poll_timer: QTimer | None = None
        self._last_mtime_ns: int | None = None
        self._theme_name: str = 'eve'
        self._language: str = 'plain'
        self.auto_completion_port = auto_completion_port
        self._request_token = 0 # monotonic int bump each cursor change
        self._ac_task = None
        self._ac_file_context_task = None
        self._ghost_text = None  # Placeholder for ghost text functionality
        self._ghost_pos = None  # Position for ghost text
        self._ghost_visible = False  # Whether ghost text is currently visible
        self._ghost_full = ""  # full multiline completion
        self._file_path = file_path  # Store the file path for reference
        self.file_context = None # Context that will be sent to the LLM for auto-completion
        # --- add to __init__ ---
        # Error cooldown gate to avoid spamming server/logs on repeated failures
        try:
            cd_env = os.environ.get("EVE_AC_ERROR_COOLDOWN", "3.0")
            cd_secs = float(cd_env) if cd_env is not None else 3.0
        except Exception:
            cd_secs = 3.0
        try:
            self._ac_error_cooldown = CooldownGate(seconds=cd_secs)
        except Exception:
            self._ac_error_cooldown = CooldownGate(seconds=3.0)

        # Find/Replace state
        self._find_text: str = ""
        self._replace_text: str = ""
        self._find_case: bool = False
        self._find_whole: bool = False
        self._find_regex: bool = False
        self._find_bar_visible: bool = False

        # Process port in server_info.json read the file
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        f = QFont('Menlo, Consolas, monospace')
        f.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(f)

        # Line number gutter (simple, always-on)
        try:
            self._line_number_area = LineNumberArea(self)
            self.blockCountChanged.connect(self._update_line_number_area_width)
            self.updateRequest.connect(self._update_line_number_area)
            self.cursorPositionChanged.connect(self._line_number_area.update)
            self._update_line_number_area_width(0)
        except Exception:
            self._line_number_area = None

        # Preselect language from provided path (if any) and attach highlighter
        if self._path:
            try:
                self._language = get_language_for_path(self._path.name)
            except Exception:
                self._language = 'plain'
        self._recreate_highlighter()

        # Re-emit modification changes in a stable signal for TabManager
        self.document().modificationChanged.connect(self.modifiedChanged)

        # Connect cursor position changes to trigger auto-completion
        self.cursorPositionChanged.connect(self._on_cursor_changed)

        # Also update find highlights on any text change
        self.textChanged.connect(self._on_text_changed_for_find)
        # Also trigger autocomplete on typing (simple, immediate)
        try:
            self.textChanged.connect(self._on_cursor_changed)
        except Exception:
            pass
        if path:
            self.load_file(path)
        else:
            self._ensure_watcher()

        # Receive completion results on UI thread
        try:
            self.completionReady.connect(self._on_completion_ready)
        except Exception:
            pass

        # Kick off an initial autocomplete fetch shortly after creation
        try:
            QTimer.singleShot(300, self._on_cursor_changed)
        except Exception:
            pass

    # ------------------- Lifecycle helpers and cleanup -------------------
    def _on_destroyed(self, *_):
        # Note: This runs when the C++ object is being destroyed; mark as not alive
        self._alive = False

    def _is_valid(self) -> bool:
        try:
            from shiboken6 import isValid  # type: ignore
            return bool(self._alive) and isValid(self)
        except Exception:
            # If shiboken not available for any reason, rely on the flag only
            return bool(self._alive)

    def dispose(self) -> None:
        """Dispose resources and make the editor inert. Idempotent."""
        if getattr(self, '_disposed', False):
            self._alive = False
            return
        self._disposed = True
        self._alive = False

        # Cancel async tasks
        try:
            if self._ac_task is not None:
                try:
                    self._ac_task.cancel()
                except Exception:
                    pass
                self._ac_task = None
        except Exception:
            pass
        try:
            if self._ac_file_context_task is not None:
                try:
                    self._ac_file_context_task.cancel()
                except Exception:
                    pass
                self._ac_file_context_task = None
        except Exception:
            pass

        # Disconnect signals that might schedule work
        for sig, slot in [
            (getattr(self, 'cursorPositionChanged', None), self._on_cursor_changed),
            (getattr(self, 'textChanged', None), self._on_cursor_changed),
            (getattr(self, 'textChanged', None), self._on_text_changed_for_find),
            (getattr(self, 'completionReady', None), self._on_completion_ready),
        ]:
            try:
                if sig is not None:
                    sig.disconnect(slot)
            except Exception:
                pass

        # Stop poll timer
        try:
            if self._poll_timer is not None:
                try:
                    if self._poll_timer.isActive():
                        self._poll_timer.stop()
                except Exception:
                    pass
                try:
                    self._poll_timer.deleteLater()
                except Exception:
                    pass
                self._poll_timer = None
        except Exception:
            pass

        # FileSystemWatcher cleanup
        try:
            if self._watcher is not None:
                try:
                    fs = self._watcher.files()
                    if fs:
                        self._watcher.removePaths(fs)
                except Exception:
                    pass
                try:
                    ds = self._watcher.directories()
                    if ds:
                        self._watcher.removePaths(ds)
                except Exception:
                    pass
                # Disconnect slots
                try:
                    self._watcher.fileChanged.disconnect(self._on_file_changed)
                except Exception:
                    pass
                try:
                    self._watcher.directoryChanged.disconnect(self._on_directory_changed)
                except Exception:
                    pass
                try:
                    self._watcher.deleteLater()
                except Exception:
                    pass
                self._watcher = None
        except Exception:
            pass

        # Clear transient visuals/state
        try:
            self.clear_ghost_text()
        except Exception:
            pass

    def closeEvent(self, e: QtGui.QCloseEvent):  # type: ignore[override]
        try:
            self.dispose()
        except Exception:
            pass
        super().closeEvent(e)

    @property
    def path(self) -> Path | None:
        return self._path

    def set_theme(self, name: str) -> None:
        """Apply syntax theme to the current highlighter."""
        self._theme_name = name or 'eve'
        try:
            if hasattr(self, 'highlighter') and hasattr(self.highlighter, 'set_theme'):
                self.highlighter.set_theme(self._theme_name)
        except Exception:
            # Be resilient; syntax colors just won't update if something goes wrong
            pass

    def _recreate_highlighter(self) -> None:
        """Recreate a language-appropriate highlighter for the current document."""
        try:
            # Clean up previous highlighter instance attached to the document
            old = getattr(self, 'highlighter', None)
            if old is not None:
                try:
                    old.deleteLater()
                except Exception:
                    pass
        finally:
            pass
        try:
            fp = str(self._path) if getattr(self, "_path", None) else None
            self.highlighter = create_highlighter(self.document(), self._theme_name, self._language, fp)
        except ImportError as ie:
            # Pygments is required; avoid GUI calls from non-UI/headless contexts
            try:
                print("[Highlighter] Missing dependency: Pygments is required for syntax highlighting.\n"
                      "Please run: pip install -r requirements.txt, then restart the IDE.")
            except Exception:
                pass
            self.highlighter = None
            return
            return
        except Exception as e:
            # Do not fallback to regex/plain; keep Pygments-only and avoid crashing the editor
            try:
                print(f"[Highlighter] Error creating PygmentsHighlighter for {self._language}: {e}")
            except Exception:
                pass
            self.highlighter = None
            return
    def _ensure_watcher(self) -> None:
        if self._watcher is None:
            self._watcher = QFileSystemWatcher(self)
            self._watcher.fileChanged.connect(self._on_file_changed)
            self._watcher.directoryChanged.connect(self._on_directory_changed)
        self._rewatch_current_path()

    def _ensure_polling(self) -> None:
        if self._poll_timer is None:
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(100)  # 10 Hz for snappy reloads
            self._poll_timer.timeout.connect(self._check_file_mtime)
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    def _rewatch_current_path(self) -> None:
        if not self._watcher:
            return
        # Clear prior watched targets (files and directories)
        try:
            fs = self._watcher.files()
            if fs:
                self._watcher.removePaths(fs)
            ds = self._watcher.directories()
            if ds:
                self._watcher.removePaths(ds)
        except Exception:
            pass
        # Watch current file and its parent directory if they exist
        try:
            if self._path and self._path.exists():
                self._watcher.addPath(str(self._path))
            if self._path and self._path.parent.exists():
                self._watcher.addPath(str(self._path.parent))
        except Exception:
            pass

    def _current_mtime_ns(self) -> int | None:
        try:
            if self._path and self._path.exists():
                return self._path.stat().st_mtime_ns
        except Exception:
            return None
        return None

    def _check_file_mtime(self) -> None:
        # Polling fallback for external changes (handles missed FS events and coarse timestamp granularity)
        if not self._path or self._suppress_fs_events:
            return
        curr = self._current_mtime_ns()
        if curr is None:
            return
        if self._last_mtime_ns is None:
            self._last_mtime_ns = curr
            return

        changed_detected = (curr != self._last_mtime_ns)

        # If timestamps are unchanged but the document is unmodified, verify content divergence
        if not changed_detected and not self.document().isModified():
            try:
                disk_text = self._path.read_text(encoding='utf-8')
            except Exception:
                disk_text = None
            if disk_text is not None and disk_text != self.toPlainText():
                changed_detected = True

        if changed_detected:
            self.externalFileChanged.emit(str(self._path))
            if not self.document().isModified():
                self.load_file(self._path)
                self.fileReloaded.emit(str(self._path))
                self._last_mtime_ns = self._current_mtime_ns()
            else:
                # Do not overwrite user edits; just record timestamp
                self._last_mtime_ns = curr

    def _on_directory_changed(self, dir_path: str) -> None:
        # When the containing directory changes, re-check the file for changes
        if not self._path:
            return
        try:
            if Path(dir_path).resolve() != self._path.parent.resolve():
                return
        except Exception:
            if Path(dir_path) != self._path.parent:
                return
        # Use the same logic as polling check
        self._check_file_mtime()

    def _on_file_changed(self, file_path: str) -> None:
        # Ignore reloads triggered by our own save (short grace period)
        if self._suppress_fs_events:
            return
        self.externalFileChanged.emit(file_path)
        if not self._path:
            return
        # Compare resolved paths to avoid macOS /var vs /private/var differences
        try:
            changed = Path(file_path)
            if changed.resolve() != self._path.resolve():
                # Not the same file; ignore
                return
        except Exception:
            # Fallback to direct comparison if resolve() fails
            if Path(file_path) != self._path:
                return
        # Only auto-reload if there are no unsaved edits to avoid data loss
        if not self.document().isModified():
            self.load_file(self._path)
            self.fileReloaded.emit(str(self._path))
        # Ensure the watcher continues watching the current path (some platforms require re-adding)
        self._rewatch_current_path()

    def _on_cursor_changed(self):
        # Increment request token to ensure only the latest request is processed
        self._request_token += 1
        current_token = self._request_token

        # Cancel any previous auto-completion task if it exists
        if self._ac_task:
            try:
                self._ac_task.cancel()
            except Exception:
                pass
        if self._ac_file_context_task:
            try:
                self._ac_file_context_task.cancel()
            except Exception:
                pass

        # Update any visible ghost to account for newly typed text, or clear if mismatched
        try:
            self._maybe_trim_ghost_on_user_typing()
        except Exception:
            pass

        # Local fallback ghost is disabled: only show server completions when available.

        # Respect error cooldown: avoid repeated server calls during recent failures
        try:
            if getattr(self, "_ac_error_cooldown", None) and self._ac_error_cooldown.in_cooldown():
                return
        except Exception:
            pass

        # If an asyncio event loop is running (e.g., via qasync), use async path
        try:
            _ = asyncio.get_running_loop()
            self._ac_task = asyncio.create_task(self._on_cursor_changed_async(current_token))
            self._ac_file_context_task = asyncio.create_task(self.fetch_file_context(str(self._path) if self._path else self._file_path, self.auto_completion_port))
            return
        except RuntimeError:
            # Fallback for plain PySide apps without qasync: thread-based fetch
            self._start_completion_thread(current_token)
            return

    def _start_completion_thread(self, current_token: int) -> None:
        import threading
        # Ensure we have a usable port; try resolving if missing
        if self.auto_completion_port <= 0:
            try:
                p = resolve_port(0)
                if p > 0:
                    self.auto_completion_port = p
            except Exception:
                pass
        if self.auto_completion_port <= 0:
            return
        # Snapshot state
        cursor = self.textCursor()
        position = cursor.position()
        doc = self.document()
        text = doc.toPlainText()
        prefix = text[max(position - 400, 0):position]
        suffix = text[position:min(position + 400, len(text))]
        if prefix == "":
            prefix_payload = ["START OF FILE"]
        else:
            prefix_payload = prefix

        def worker():
            comp_text = ""
            try:
                # Build or refresh file-dependent context on the worker thread (non-blocking UI)
                ctx = self.file_context
                if not ctx:
                    try:
                        fp = str(self._path) if self._path else self._file_path
                        if fp:
                            ctx = CodeIndexer().return_context(fp)
                            self.file_context = ctx
                        else:
                            ctx = {}
                    except Exception:
                        ctx = {}
                payload = {"prefix": prefix_payload, "suffix": suffix, "context": ctx}

                # Respect error cooldown: avoid attempting during cooldown window
                cd = getattr(self, "_ac_error_cooldown", None)
                if not (cd and cd.in_cooldown()):
                    data = sync_post_json(self.auto_completion_port, "/autocomplete", payload=payload, timeout=5)
                    comp_text = data.get("completion", "")
                    if isinstance(comp_text, list):
                        comp_text = comp_text[0] if comp_text else ""
                    if not isinstance(comp_text, str):
                        comp_text = str(comp_text)
            except Exception as e:
                # Log only once per cooldown window and start cooldown
                try:
                    cd = getattr(self, "_ac_error_cooldown", None)
                    if cd:
                        if not cd.in_cooldown():
                            print("Error contacting auto-completion server (thread):", e)
                        cd.trip(message=str(e))
                    else:
                        print("Error contacting auto-completion server (thread):", e)
                except Exception:
                    pass
                comp_text = ""
            # Always deliver via signal to UI thread; handler filters out non-meaningful text
            try:
                try:
                    from shiboken6 import isValid  # type: ignore
                except Exception:
                    def isValid(_):  # type: ignore
                        return True
                if not (getattr(self, "_alive", False) and isValid(self)):
                    return
                self.completionReady.emit(current_token, comp_text)
            except Exception:
                pass

        try:
            t = threading.Thread(target=worker, daemon=True)
            t.start()
        except Exception:
            pass

    def set_ghost_text(self, text: str, position: int):
        """Set ghost text at a specific position in the editor."""
        if not self._is_valid():
            return
        self._ghost_text = text or ""
        self._ghost_pos = int(position)
        self._ghost_visible = bool(text)
        try:
            print(f"[ghost] pos={self._ghost_pos} text={self._ghost_text[:60]!r}")
        except Exception:
            pass
        self.viewport().update()  # Trigger a repaint to show ghost text

    # Override paintEvent to draw ghost text
    def paintEvent(self, event: QtGui.QPaintEvent):
        super().paintEvent(event)
        if self._ghost_visible and self._ghost_text and isinstance(self._ghost_pos, int) and self._ghost_pos >= 0:
            cursor = QtGui.QTextCursor(self.document())
            cursor.setPosition(self._ghost_pos)
            rect = self.cursorRect(cursor)
            fm = self.fontMetrics()
            baseline = rect.y() + fm.ascent()

            avail = max(0, self.viewport().width() - rect.x() - 4)
            shown = fm.elidedText(self._ghost_text, QtCore.Qt.ElideRight, max(1, avail))
            if not shown:
                shown = "…"

            color = self.palette().color(QtGui.QPalette.Text)
            try:
                color.setAlphaF(0.55)
            except Exception:
                pass
            painter = QtGui.QPainter(self.viewport())
            painter.setPen(color)
            painter.drawText(rect.x(), baseline, shown)
            # painter.end() optional in PySide, local scope is fine

    def clear_ghost_text(self):
        """Clear any ghost text currently set."""
        if not self._is_valid():
            return
        self._ghost_text = None
        self._ghost_pos = None
        self._ghost_visible = False
        self.viewport().update()

    def _is_meaningful_completion(self, s: str) -> bool:
        """Return True only for non-empty, non-stub completions.
        - Filters out empty/whitespace
        - Filters out local/server stub strings like "test_completion:..."
        """
        try:
            t = (s or "").strip()
            if not t:
                return False
            if t.startswith("test_completion:"):
                return False
            return True
        except Exception:
            return False

    def _has_non_ws_suffix_on_line(self) -> bool:
        """Return True if there is any non-whitespace text to the right of the cursor until end-of-line."""
        try:
            c = QtGui.QTextCursor(self.textCursor())
            c.setPosition(self.textCursor().position(), QtGui.QTextCursor.MoveAnchor)
            c.movePosition(QtGui.QTextCursor.EndOfLine, QtGui.QTextCursor.KeepAnchor)
            s = c.selectedText()  # Note: Qt may use \u2029 for paragraph separators; not present in-line
            return bool(s and s.strip())
        except Exception:
            return False

    def _should_show_ghost_here(self) -> bool:
        """Only show ghost if it won't overlay actual inline text (no non-whitespace suffix on this line)."""
        return not self._has_non_ws_suffix_on_line()

    def _maybe_trim_ghost_on_user_typing(self) -> bool:
        """If the user typed characters that match the start of the current ghost,
        trim the shown suggestion to the remaining tail and move the anchor forward.
        If the typed characters do not match, clear the ghost.
        Returns True if an update/clear was applied, False otherwise.
        """
        try:
            if not (self._ghost_visible and isinstance(self._ghost_pos, int) and self._ghost_pos >= 0 and self._ghost_full):
                return False
            cur = self.textCursor()
            pos = int(cur.position())
            # If user moved left of ghost anchor or no movement, clear or ignore accordingly
            if pos < self._ghost_pos:
                self.clear_ghost_text()
                return True
            if pos == self._ghost_pos:
                return False
            doc_text = self.document().toPlainText()
            if self._ghost_pos > len(doc_text) or pos > len(doc_text):
                self.clear_ghost_text()
                return True
            typed = doc_text[self._ghost_pos:pos]
            if not typed:
                return False
            if self._ghost_full.startswith(typed):
                # Advance anchor and shrink suggestion
                self._ghost_pos = pos
                self._ghost_full = self._ghost_full[len(typed):]
                if self._ghost_full.strip():
                    first_line = self._ghost_full.splitlines()[0] if "\n" in self._ghost_full else self._ghost_full.strip()
                    self.set_ghost_text(first_line, self._ghost_pos)
                else:
                    self.clear_ghost_text()
                return True
            # Mismatch: clear stale ghost
            self.clear_ghost_text()
            return True
        except Exception:
            return False

    def _on_completion_ready(self, token: int, comp_text: str) -> None:
        # Runs on UI thread via queued signal
        if not self._is_valid():
            return
        if token != self._request_token:
            return
        if not self._is_meaningful_completion(comp_text):
            return
        # Do not overlay on actual inline text
        if not self._should_show_ghost_here():
            return
        cur = self.textCursor()
        anchor_pos = cur.position()
        self._ghost_full = comp_text
        _lines = [ln for ln in comp_text.splitlines() if ln.strip()]
        first_line = _lines[0] if _lines else comp_text.strip()
        self.set_ghost_text(first_line, anchor_pos)

    async def fetch_completion(self, prefix: str, suffix: str, context: str, port: int) -> str:
        # Use centralized client with retry + port re-resolve
        payload = {"prefix": prefix, "suffix": suffix, "context": context}

        # Respect cooldown: if in cooldown, skip contacting the server
        cd = getattr(self, "_ac_error_cooldown", None)
        if cd and cd.in_cooldown():
            return "", {}
        try:
            data = await async_post_json(port, "/autocomplete", payload=payload, timeout=5)
            comp = data.get("completion", "")
            if isinstance(comp, list):
                comp = comp[0] if comp else ""
            if not isinstance(comp, str):
                comp = str(comp)
            return comp, data
        except Exception as e:
            # Log only once per cooldown and trip it
            try:
                if cd:
                    if not cd.in_cooldown():
                        print("Error contacting auto-completion server:", e)
                    cd.trip(message=str(e))
                else:
                    print("Error contacting auto-completion server:", e)
            except Exception:
                pass
            return "", {}

    async def fetch_file_context(self, file_path: str, port: int) -> str:
        indexer = CodeIndexer()
        loop = asyncio.get_event_loop()
        context = await loop.run_in_executor(None, indexer.return_context, file_path)
        self.file_context = context
        await asyncio.sleep(5)  # Avoid hammering the server too fast
        return

    async def _on_cursor_changed_async(self, current_token: int):
        await asyncio.sleep(0.2)
        if current_token != self._request_token:
            return
        if not self._is_valid():
            return

        # Respect cooldown again on async path
        try:
            if getattr(self, "_ac_error_cooldown", None) and self._ac_error_cooldown.in_cooldown():
                return
        except Exception:
            pass

        # Ensure port is resolved when using async path
        if self.auto_completion_port <= 0:
            try:
                p = await asyncio.to_thread(resolve_port, 0)
                if p > 0:
                    self.auto_completion_port = p
            except Exception:
                pass
        if not self._is_valid():
            return

        cursor = self.textCursor()
        position = cursor.position()
        doc = self.document()
        text = doc.toPlainText()
        prefix = text[max(position - 400, 0):position]
        suffix = text[position:min(position + 400, len(text))]
        try:
            if prefix == "":
                prefix = ["START OF FILE"]
            full, full_json = await self.fetch_completion(prefix, suffix, self.file_context if self.file_context else {}, self.auto_completion_port)
            if not isinstance(full, str):
                full = str(full)
        except Exception as e:
            # Log once per cooldown and trip it
            try:
                cd = getattr(self, "_ac_error_cooldown", None)
                if cd:
                    if not cd.in_cooldown():
                        print("Error contacting auto-completion server:", e)
                    cd.trip(message=str(e))
                else:
                    print("Error contacting auto-completion server:", e)
            except Exception:
                pass
            return
        self.clear_ghost_text()
        if current_token != self._request_token:
            return
        if not self._is_valid():
            return
        if not self._is_meaningful_completion(full):
            return
        # Do not overlay on actual inline text
        if not self._should_show_ghost_here():
            return
        # Anchor to current caret position; tolerate small movement since snapshot
        cur = self.textCursor()
        anchor_pos = cur.position()
        self._ghost_full = full
        _lines = [ln for ln in full.splitlines() if ln.strip()]
        first_line = _lines[0] if _lines else full.strip()
        self.set_ghost_text(first_line, anchor_pos)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if (event.key() == QtCore.Qt.Key_Tab and
            self._ghost_visible and
            isinstance(self._ghost_pos, int) and self._ghost_pos >= 0 and
            self._ghost_full):

            cur = self.textCursor()
            # If cursor moved, snap to the ghost anchor
            if cur.position() != self._ghost_pos:
                cur.setPosition(self._ghost_pos)
            # replace any selection with insertion point only
            if cur.hasSelection():
                cur.setPosition(cur.position())  # collapse

            cur.insertText(self._ghost_full)  # inserts newlines too
            self.setTextCursor(cur)
            self.clear_ghost_text()
            event.accept()
            return

        # Otherwise, default behavior (incl. Shift+Tab unindent, etc.)
        super().keyPressEvent(event)

    # ------------------- Line number area helpers -------------------
    def line_number_area_width(self) -> int:
        try:
            digits = len(str(max(1, self.blockCount())))
            fm = self.fontMetrics()
            # 3px left + digits * char width + 6px right padding
            return 3 + fm.horizontalAdvance('9') * digits + 6
        except Exception:
            return 32

    def _update_line_number_area_width(self, _=0) -> None:
        try:
            self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)
        except Exception:
            pass

    def _update_line_number_area(self, rect: QtCore.QRect, dy: int) -> None:
        try:
            if not hasattr(self, "_line_number_area") or self._line_number_area is None:
                return
            if dy:
                self._line_number_area.scroll(0, dy)
            else:
                self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
            if rect.contains(self.viewport().rect()):
                # Update width and geometry when full viewport changes
                self._update_line_number_area_width(0)
        except Exception:
            pass

    def _line_number_area_paint_event(self, event: QtGui.QPaintEvent) -> None:
        try:
            if not hasattr(self, "_line_number_area") or self._line_number_area is None:
                return
            painter = QtGui.QPainter(self._line_number_area)
            painter.setClipRect(event.rect())

            pal = self.palette()
            base_color = pal.color(QtGui.QPalette.Base)
            # Slightly darker than editor background for subtle contrast
            bg = QtGui.QColor(base_color)
            try:
                bg = base_color.darker(104)
            except Exception:
                pass
            painter.fillRect(event.rect(), bg)

            block = self.firstVisibleBlock()
            block_number = block.blockNumber()
            top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
            bottom = top + int(self.blockBoundingRect(block).height())

            fm = self.fontMetrics()
            width = self._line_number_area.width()
            # Colors for numbers
            num_color = pal.color(QtGui.QPalette.Mid)
            cur_color = pal.color(QtGui.QPalette.Text)

            while block.isValid() and top <= event.rect().bottom():
                if block.isVisible() and bottom >= event.rect().top():
                    number = str(block_number + 1)
                    painter.setPen(cur_color if block_number == self.textCursor().blockNumber() else num_color)
                    painter.drawText(0, top, width - 4, fm.height(), QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, number)
                block = block.next()
                block_number += 1
                top = bottom
                bottom = top + int(self.blockBoundingRect(block).height())

            # Right border line for gutter
            try:
                border = pal.color(QtGui.QPalette.Mid)
                painter.setPen(border)
                painter.drawLine(width - 1, event.rect().top(), width - 1, event.rect().bottom())
            except Exception:
                pass
        except Exception:
            pass

    def load_file(self, path: Path):
        self._path = Path(path)
        self._file_path = str(self._path)
        try:
            text = self._path.read_text(encoding='utf-8')
        except Exception as e:
            text = f'# Error opening {path}: {e}\n'
        self.setPlainText(text)
        # Reset modified state after setting fresh content
        self.document().setModified(False)
        # Update last known mtime for polling
        self._last_mtime_ns = self._current_mtime_ns()
        # Detect language from new path and recreate highlighter
        try:
            self._language = get_language_for_path(self._path.name)
        except Exception:
            self._language = 'plain'
        self._recreate_highlighter()
        self._ensure_watcher()
        self._ensure_polling()
        # Refresh highlights if find is active
        self._refresh_find_highlights()

    def save(self):
        if not self._path:
            return False
        try:
            # Suppress file watcher reloads that may be triggered by our own write
            self._suppress_fs_events = True
            self._path.write_text(self.toPlainText(), encoding='utf-8')
            self.document().setModified(False)
            # Update last known mtime to match our save
            self._last_mtime_ns = self._current_mtime_ns()
            # Clear suppression shortly after the write completes
            QTimer.singleShot(250, self._clear_fs_suppression)
            return True
        except Exception:
            return False

    def _clear_fs_suppression(self):
        self._suppress_fs_events = False

    # ------------------- Find/Replace API -------------------
    def show_find_bar(self):
        """Show a compact inline Find/Replace bar over the editor viewport."""
        try:
            from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QToolButton
        except Exception:
            # Fallback to state-only if widgets cannot be imported
            self._find_bar_visible = True
            return

        bar = getattr(self, "_find_bar", None)
        if bar is None:
            # Create overlay bar parented to viewport for proper positioning/scrolling
            bar = QWidget(self.viewport())
            bar.setObjectName("findReplaceBar")
            try:
                bar.setAutoFillBackground(True)
            except Exception:
                pass

            lay = QHBoxLayout(bar)
            lay.setContentsMargins(6, 6, 6, 6)
            lay.setSpacing(4)

            # Find input
            find_edit = QLineEdit(bar)
            find_edit.setPlaceholderText("Find")
            lay.addWidget(find_edit, 1)

            # Prev / Next
            btn_prev = QToolButton(bar)
            btn_prev.setText("Prev")
            btn_prev.setToolTip("Find previous")
            lay.addWidget(btn_prev)

            btn_next = QToolButton(bar)
            btn_next.setText("Next")
            btn_next.setToolTip("Find next")
            lay.addWidget(btn_next)

            # Replace input
            repl_edit = QLineEdit(bar)
            repl_edit.setPlaceholderText("Replace")
            lay.addWidget(repl_edit, 1)

            # Replace one / all
            btn_repl = QToolButton(bar)
            btn_repl.setText("Replace")
            btn_repl.setToolTip("Replace current match")
            lay.addWidget(btn_repl)

            btn_all = QToolButton(bar)
            btn_all.setText("All")
            btn_all.setToolTip("Replace all matches")
            lay.addWidget(btn_all)

            # Case toggle (minimal option for simplicity)
            btn_case = QToolButton(bar)
            btn_case.setText("Aa")
            btn_case.setCheckable(True)
            btn_case.setToolTip("Case sensitive")
            lay.addWidget(btn_case)

            # Close
            btn_close = QToolButton(bar)
            btn_close.setText("×")
            btn_close.setToolTip("Close find/replace")
            lay.addWidget(btn_close)

            # Store refs on the bar for eventFilter access
            bar.find_edit = find_edit
            bar.replace_edit = repl_edit

            # Wire up behavior to existing editor API
            find_edit.textChanged.connect(self.set_find_text)
            repl_edit.textChanged.connect(self.set_replace_text)
            btn_prev.clicked.connect(self.find_prev)
            btn_next.clicked.connect(self.find_next)
            btn_repl.clicked.connect(self.replace_one)
            btn_all.clicked.connect(self.replace_all)
            btn_case.toggled.connect(lambda checked: self.set_find_options(
                case_sensitive=bool(checked), whole_word=self._find_whole, regex=self._find_regex))
            btn_close.clicked.connect(self.hide_find_bar)

            # Keyboard handling: Enter for next/prev, Escape to close (via event filter)
            try:
                find_edit.installEventFilter(self)
                repl_edit.installEventFilter(self)
                bar.installEventFilter(self)
            except Exception:
                pass

            self._find_bar = bar

        # Seed current state
        try:
            self._find_bar.find_edit.setText(self._find_text)
            self._find_bar.replace_edit.setText(self._replace_text)
        except Exception:
            pass

        self._find_bar_visible = True

        # Ensure parent is visible so the overlay child can be visible as well (especially in headless tests)
        try:
            if not self.isVisible():
                self.show()
        except Exception:
            pass

        self._find_bar.show()
        self._find_bar.raise_()
        self._position_find_bar()
        try:
            self._find_bar.find_edit.setFocus()
            if self._find_text:
                self._find_bar.find_edit.selectAll()
        except Exception:
            pass

    def hide_find_bar(self):
        """Hide the inline Find/Replace bar."""
        self._find_bar_visible = False
        try:
            bar = getattr(self, "_find_bar", None)
            if bar:
                bar.hide()
        except Exception:
            pass
        # If no search text, clear highlights for a clean view
        if not self._find_text:
            self.setExtraSelections([])

    def _position_find_bar(self):
        """Position the find bar at the top-right of the viewport with a small margin."""
        try:
            bar = getattr(self, "_find_bar", None)
            if not bar or not bar.isVisible():
                return
            m = 8
            try:
                bar.adjustSize()
            except Exception:
                pass
            vr = self.viewport().rect()
            x = vr.right() - bar.width() - m
            y = vr.top() + m
            try:
                bar.move(x, y)
                bar.raise_()
            except Exception:
                pass
        except Exception:
            pass

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        try:
            if hasattr(self, "_line_number_area") and self._line_number_area is not None:
                cr = self.contentsRect()
                self._line_number_area.setGeometry(QtCore.QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
        except Exception:
            pass
        self._position_find_bar()

    def eventFilter(self, obj, event):
        try:
            if event.type() == QtCore.QEvent.KeyPress:
                key = event.key()
                mods = event.modifiers()
                bar = getattr(self, "_find_bar", None)
                if bar and (obj is bar or getattr(bar, 'find_edit', None) is obj or getattr(bar, 'replace_edit', None) is obj):
                    if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                        # Enter in Find -> Next (Shift+Enter -> Prev); Enter in Replace -> Replace one
                        if obj is getattr(bar, 'find_edit', None):
                            if mods & QtCore.Qt.ShiftModifier:
                                self.find_prev()
                            else:
                                self.find_next()
                            return True
                        if obj is getattr(bar, 'replace_edit', None):
                            self.replace_one()
                            return True
                    elif key == QtCore.Qt.Key_Escape:
                        self.hide_find_bar()
                        try:
                            self.setFocus()
                        except Exception:
                            pass
                        return True
        except Exception:
            pass
        try:
            return super().eventFilter(obj, event)
        except Exception:
            return False

    def _on_text_changed_for_find(self):
        """Refresh find highlights on any text change, or clear if no find text set."""
        if self._find_text:
            self._refresh_find_highlights()
        else:
            self.setExtraSelections([])

    def set_find_text(self, text: str):
        self._find_text = text or ""
        self._refresh_find_highlights()

    def set_replace_text(self, text: str):
        self._replace_text = text or ""

    def set_find_options(self, case_sensitive: bool | None = None, whole_word: bool | None = None, regex: bool | None = None) -> None:
        if case_sensitive is not None:
            self._find_case = bool(case_sensitive)
        if whole_word is not None:
            self._find_whole = bool(whole_word)
        if regex is not None:
            self._find_regex = bool(regex)
        self._refresh_find_highlights()

    def _qt_find_flags(self, backward: bool = False) -> QtGui.QTextDocument.FindFlags:
        flags = QtGui.QTextDocument.FindFlags()
        # Use QTextDocument flags to drive case sensitivity and whole word handling
        if self._find_case:
            flags |= QtGui.QTextDocument.FindFlag.FindCaseSensitively
        if self._find_whole:
            flags |= QtGui.QTextDocument.FindFlag.FindWholeWords
        if backward:
            flags |= QtGui.QTextDocument.FindFlag.FindBackward
        return flags

    def _qt_pattern(self) -> QtCore.QRegularExpression:
        """Build a QRegularExpression based on current options and text."""
        try:
            txt = self._find_text or ""
            if not txt:
                return QtCore.QRegularExpression()
            if self._find_regex:
                rx = QtCore.QRegularExpression(txt)
            else:
                esc = QtCore.QRegularExpression.escape(txt)
                if self._find_whole:
                    esc = r"\b" + esc + r"\b"
                rx = QtCore.QRegularExpression(esc)
            if not self._find_case:
                rx.setPatternOptions(QtCore.QRegularExpression.CaseInsensitiveOption)
            return rx
        except Exception:
            # Fallback: best-effort regex
            try:
                return QtCore.QRegularExpression(self._find_text or "")
            except Exception:
                return QtCore.QRegularExpression()
    def _refresh_find_highlights(self) -> None:
        """Highlight all matches of the current find pattern without moving the caret."""
        try:
            text = self._find_text or ""
            if not text.strip():
                self.setExtraSelections([])
                return
            pattern = self._qt_pattern()
            flags = self._qt_find_flags(False)
            doc = self.document()
            # Iterate matches using QTextDocument.find without disturbing the editor cursor
            sels: list = []
            cursor = QtGui.QTextCursor(doc)
            cursor.movePosition(QtGui.QTextCursor.Start)
            while True:
                cur = doc.find(pattern, cursor, flags)
                if cur.isNull() or not cur.hasSelection():
                    break
                sel = QTextEdit.ExtraSelection()
                sel.cursor = cur
                fmt = QtGui.QTextCharFormat()
                try:
                    fmt.setBackground(QtGui.QColor(255, 235, 59, 96))  # semi-transparent yellow
                except Exception:
                    pass
                sel.format = fmt
                sels.append(sel)
                # Continue search after this match
                cursor.setPosition(cur.selectionEnd())
            self.setExtraSelections(sels)
        except Exception:
            # Be resilient; highlight failure should not break editing
            try:
                self.setExtraSelections([])
            except Exception:
                pass

    def _wrap_find_once(self, backward: bool = False) -> bool:
        if not self._find_text:
            return False
        pattern = self._qt_pattern()
        flags = self._qt_find_flags(backward)
        # Try from current position
        if self.find(pattern, flags):
            return True
        # Wrap to start/end and try again
        if backward:
            self.moveCursor(QtGui.QTextCursor.End)
        else:
            self.moveCursor(QtGui.QTextCursor.Start)
        return self.find(pattern, flags)

    def find_next(self) -> bool:
        ok = self._wrap_find_once(backward=False)
        self._refresh_find_highlights()
        return ok

    def find_prev(self) -> bool:
        ok = self._wrap_find_once(backward=True)
        self._refresh_find_highlights()
        return ok

    def replace_one(self) -> bool:
        if not self._find_text:
            return False
        cur = self.textCursor()
        if not cur.hasSelection():
            if not self.find_next():
                return False
            cur = self.textCursor()
            if not cur.hasSelection():
                return False
        cur.insertText(self._replace_text)
        self._refresh_find_highlights()
        return True

    def replace_all(self) -> int:
        if not self._find_text:
            return 0
        pattern = self._qt_pattern()
        flags = self._qt_find_flags(backward=False)
        count = 0
        cur = self.textCursor()
        cur.beginEditBlock()
        try:
            # Start from beginning for deterministic behavior
            self.moveCursor(QtGui.QTextCursor.Start)
            while self.find(pattern, flags):
                tc = self.textCursor()
                if not tc.hasSelection():
                    break
                tc.insertText(self._replace_text)
                count += 1
        finally:
            cur.endEditBlock()
        self._refresh_find_highlights()
        return count


class TabManager(QTabWidget):
    editorCreated = Signal(object)  # emits CodeEditor when a new editor is created

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._close_index)
        self._theme_name: str = 'eve'

    def set_theme(self, name: str) -> None:
        """Apply syntax theme to all open editors and remember it for new tabs."""
        self._theme_name = name or 'eve'
        for i in range(self.count()):
            w = self.widget(i)
            if isinstance(w, CodeEditor):
                w.set_theme(self._theme_name)

    def _close_index(self, idx: int):
        w = self.widget(idx)
        if hasattr(w, 'document') and w.document().isModified():
            # TODO: prompt to save
            pass
        # Dispose editor resources before removal
        try:
            if isinstance(w, CodeEditor):
                w.dispose()
        except Exception:
            pass
        self.removeTab(idx)
        try:
            w.deleteLater()
        except Exception:
            pass

    def _on_modified_changed(self, editor: CodeEditor, modified: bool) -> None:
        # Update tab label with asterisk on modification
        for i in range(self.count()):
            if self.widget(i) is editor:
                base = editor.path.name if editor.path else 'Untitled'
                self.setTabText(i, f'*{base}' if modified else base)
                break

    def open_file(self, path: Path, port_num: int = 0, file_path: str = "") -> CodeEditor:
        path = Path(path)
        # Reuse existing tab if open
        for i in range(self.count()):
            w = self.widget(i)
            if isinstance(w, CodeEditor) and w.path and w.path.resolve() == path.resolve():
                self.setCurrentIndex(i)
                return w
        editor = CodeEditor(path, auto_completion_port=port_num, file_path=file_path)
        editor.set_theme(self._theme_name)
        # Reflect modified state changes in tab title
        editor.modifiedChanged.connect(lambda m, e=editor: self._on_modified_changed(e, m))
        # Also refresh tab title after reload (ensures no asterisk if content fresh)
        editor.fileReloaded.connect(lambda _p, e=editor: self._on_modified_changed(e, False))

        self.addTab(editor, path.name)
        self.setCurrentWidget(editor)
        try:
            self.editorCreated.emit(editor)
        except Exception:
            pass
        return editor

    def save_current(self) -> bool:
        w = self.currentWidget()
        if isinstance(w, CodeEditor):
            ok = w.save()
            if ok:
                self.setTabText(self.currentIndex(), (w.path.name if w.path else 'Untitled'))
            return ok
        return False

    def dispose_all_editors(self) -> None:
        """Dispose all CodeEditor instances managed by this tab widget."""
        try:
            for i in range(self.count()):
                w = self.widget(i)
                if isinstance(w, CodeEditor):
                    try:
                        w.dispose()
                    except Exception:
                        pass
        except Exception:
            pass
            return False
        pattern = self._qt_pattern()
        flags = self._qt_find_flags(backward)
        # Try from current position
        if self.find(pattern, flags):
            return True
        # Wrap to start/end and try again
        if backward:
            self.moveCursor(QtGui.QTextCursor.End)
        else:
            self.moveCursor(QtGui.QTextCursor.Start)
        return self.find(pattern, flags)

    def find_next(self) -> bool:
        ok = self._wrap_find_once(backward=False)
        self._refresh_find_highlights()
        return ok

    def find_prev(self) -> bool:
        ok = self._wrap_find_once(backward=True)
        self._refresh_find_highlights()
        return ok

    def replace_one(self) -> bool:
        if not self._find_text:
            return False
        cur = self.textCursor()
        if not cur.hasSelection():
            if not self.find_next():
                return False
            cur = self.textCursor()
            if not cur.hasSelection():
                return False
        cur.insertText(self._replace_text)
        self._refresh_find_highlights()
        return True

    def replace_all(self) -> int:
        if not self._find_text:
            return 0
        pattern = self._qt_pattern()
        flags = self._qt_find_flags(backward=False)
        count = 0
        cur = self.textCursor()
        cur.beginEditBlock()
        try:
            # Start from beginning for deterministic behavior
            self.moveCursor(QtGui.QTextCursor.Start)
            while self.find(pattern, flags):
                tc = self.textCursor()
                if not tc.hasSelection():
                    break
                tc.insertText(self._replace_text)
                count += 1
        finally:
            cur.endEditBlock()
        self._refresh_find_highlights()
        return count


class TabManager(QTabWidget):
    editorCreated = Signal(object)  # emits CodeEditor when a new editor is created

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self._close_index)
        self._theme_name: str = 'eve'

    def set_theme(self, name: str) -> None:
        """Apply syntax theme to all open editors and remember it for new tabs."""
        self._theme_name = name or 'eve'
        for i in range(self.count()):
            w = self.widget(i)
            if isinstance(w, CodeEditor):
                w.set_theme(self._theme_name)

    def _close_index(self, idx: int):
        w = self.widget(idx)
        if hasattr(w, 'document') and w.document().isModified():
            # TODO: prompt to save
            pass
        # Dispose editor resources before removal
        try:
            if isinstance(w, CodeEditor):
                w.dispose()
        except Exception:
            pass
        self.removeTab(idx)
        try:
            w.deleteLater()
        except Exception:
            pass

    def _on_modified_changed(self, editor: CodeEditor, modified: bool) -> None:
        # Update tab label with asterisk on modification
        for i in range(self.count()):
            if self.widget(i) is editor:
                base = editor.path.name if editor.path else 'Untitled'
                self.setTabText(i, f'*{base}' if modified else base)
                break

    def open_file(self, path: Path, port_num: int = 0, file_path: str = "") -> CodeEditor:
        path = Path(path)
        # Reuse existing tab if open
        for i in range(self.count()):
            w = self.widget(i)
            if isinstance(w, CodeEditor) and w.path and w.path.resolve() == path.resolve():
                self.setCurrentIndex(i)
                return w
        editor = CodeEditor(path, auto_completion_port=port_num, file_path=file_path)
        editor.set_theme(self._theme_name)
        # Reflect modified state changes in tab title
        editor.modifiedChanged.connect(lambda m, e=editor: self._on_modified_changed(e, m))
        # Also refresh tab title after reload (ensures no asterisk if content fresh)
        editor.fileReloaded.connect(lambda _p, e=editor: self._on_modified_changed(e, False))

        self.addTab(editor, path.name)
        self.setCurrentWidget(editor)
        try:
            self.editorCreated.emit(editor)
        except Exception:
            pass
        return editor

    def save_current(self) -> bool:
        w = self.currentWidget()
        if isinstance(w, CodeEditor):
            ok = w.save()
            if ok:
                self.setTabText(self.currentIndex(), (w.path.name if w.path else 'Untitled'))
            return ok
        return False

    def dispose_all_editors(self) -> None:
        """Dispose all CodeEditor instances managed by this tab widget."""
        try:
            for i in range(self.count()):
                w = self.widget(i)
                if isinstance(w, CodeEditor):
                    try:
                        w.dispose()
                    except Exception:
                        pass
        except Exception:
            pass