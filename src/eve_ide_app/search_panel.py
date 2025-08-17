from __future__ import annotations
from pathlib import Path
import re
import threading
from typing import Iterable

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QCheckBox,
    QLabel, QListWidget, QListWidgetItem
)


class SearchPanel(QWidget):
    """Workspace-wide file search panel.
    - Enter a query, choose options (case, regex, whole word), click Search
    - Results list shows matches; clicking a result emits openLocation(file, line, column)
    """

    openLocation = Signal(str, int, int)  # file_path, line (1-based), column (1-based)
    searchStarted = Signal()
    searchFinished = Signal(int)  # number of results

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._root: Path | None = None
        self._thread: threading.Thread | None = None
        self._cancel = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # Controls row
        row = QHBoxLayout()
        row.addWidget(QLabel("Find:"))
        self.query = QLineEdit(self)
        self.query.setPlaceholderText("Search in workspace…")
        row.addWidget(self.query, 1)
        self.case = QCheckBox("Case")
        self.regex = QCheckBox("Regex")
        self.whole = QCheckBox("Whole")
        row.addWidget(self.case)
        row.addWidget(self.regex)
        row.addWidget(self.whole)
        self.search_btn = QPushButton("Search", self)
        self.search_btn.clicked.connect(self._on_search_clicked)
        row.addWidget(self.search_btn)
        layout.addLayout(row)

        # Results
        self.results = QListWidget(self)
        self.results.itemActivated.connect(self._on_item_activated)
        self.results.itemClicked.connect(self._on_item_activated)
        layout.addWidget(self.results, 1)

    # -------- Public API --------
    def set_root(self, path: str | Path) -> None:
        try:
            p = Path(path).resolve()
            if p.exists() and p.is_dir():
                self._root = p
        except Exception:
            pass

    def run_search(self, query: str, *, case: bool = False, regex: bool = False, whole: bool = False) -> None:
        self.query.setText(query or "")
        self.case.setChecked(bool(case))
        self.regex.setChecked(bool(regex))
        self.whole.setChecked(bool(whole))
        self._start_search()

    # -------- Internals --------
    def _on_search_clicked(self):
        self._start_search()

    def _start_search(self):
        if not self._root or not self.query.text().strip():
            self.results.clear()
            self.searchFinished.emit(0)
            return
        # Cancel any in-flight worker
        if self._thread and self._thread.is_alive():
            self._cancel = True
            try:
                self._thread.join(timeout=0.1)
            except Exception:
                pass
        self._cancel = False
        self.results.clear()
        self.searchStarted.emit()
        args = (
            self._root,
            self.query.text(),
            self.case.isChecked(),
            self.regex.isChecked(),
            self.whole.isChecked(),
        )
        self._thread = threading.Thread(target=self._worker, args=args, daemon=True)
        self._thread.start()

    def _iter_files(self, root: Path) -> Iterable[Path]:
        skip_dirs = {".git", ".hg", ".svn", "venv", ".venv", "node_modules", ".pytest_cache", "__pycache__"}
        for p in root.rglob("*"):
            if self._cancel:
                return
            try:
                if p.is_dir():
                    # rglob already recurses; we just skip emitting directories
                    continue
                # Skip typical binary or large files by extension
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".zip", ".exe", ".dll", ".so", ".dylib"}:
                    continue
                # Skip paths containing ignored directories
                parts = set(part.lower() for part in p.parts)
                if parts & {d.lower() for d in skip_dirs}:
                    continue
                yield p
            except Exception:
                continue

    def _compile_pattern(self, query: str, case: bool, regex: bool, whole: bool):
        flags = 0 if case else re.IGNORECASE
        if regex:
            try:
                rx = re.compile(query, flags)
                return rx
            except Exception:
                # Fallback to literal
                regex = False
        # Build a literal pattern
        q = re.escape(query)
        if whole:
            q = rf"\b{q}\b"
        return re.compile(q, flags)

    def _worker(self, root: Path, query: str, case: bool, regex: bool, whole: bool):
        rx = self._compile_pattern(query, case, regex, whole)
        total = 0
        for file in self._iter_files(root):
            if self._cancel:
                break
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            # Scan line by line for positions
            for i, line in enumerate(text.splitlines(), start=1):
                for m in rx.finditer(line):
                    if self._cancel:
                        break
                    col = m.start() + 1  # 1-based
                    item = QListWidgetItem()
                    item.setText(f"{file} :{i}:{col} — {line.strip()[:160]}")
                    # Store payload under both modern and legacy roles for PySide6/Qt compatibility in tests
                    payload = (str(file), i, col)
                    item.setData(Qt.UserRole, payload)
                    item.setData(32, payload)  # Qt.UserRole in some bindings/tests
                    self.results.addItem(item)
                    total += 1
        # Emit finished (from worker thread; Qt will queue to main thread)
        self.searchFinished.emit(total)

    def _on_item_activated(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole) or item.data(32)
        if not data:
            return
        file, line, col = data
        self.openLocation.emit(str(file), int(line), int(col))