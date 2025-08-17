from __future__ import annotations
from pathlib import Path
import shutil

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTreeView, QFileSystemModel, QMenu, QInputDialog, QMessageBox, QAbstractItemView
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal, QModelIndex, QDir, Qt, QPoint

from .icon_provider import EveIconProvider


class FileExplorer(QWidget):
    fileOpenRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.model = QFileSystemModel(self)
        self.model.setReadOnly(False)
        # Use QDir filter flags (Qt6)
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)

        # Keep a reference to our custom icon provider (default dark)
        self.icon_provider = EveIconProvider()
        self.model.setIconProvider(self.icon_provider)

        self.view = QTreeView(self)
        self.view.setModel(self.model)
        # Minimal, name-only appearance
        self.view.setHeaderHidden(True)
        try:
            for i in range(1, self.model.columnCount()):
                self.view.hideColumn(i)
        except Exception:
            pass
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.view.setUniformRowHeights(True)

        # Open behavior
        self.view.doubleClicked.connect(self._on_double_clicked)
        self.view.clicked.connect(self._on_clicked)        # open on single click
        self.view.activated.connect(self._on_activated)    # keyboard activation

        # Context menu support
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._on_context_menu)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.view)

    def set_root_path(self, path: str | Path):
        root = self.model.setRootPath(str(path))
        self.view.setRootIndex(root)
        # Expand a bit by default
        try:
            self.view.setExpanded(root, True)
        except Exception:
            pass
        # Ensure only name column shows (model may reconfigure after setting root)
        self.view.setHeaderHidden(True)
        try:
            for i in range(1, self.model.columnCount()):
                self.view.hideColumn(i)
        except Exception:
            pass

    def _refresh_model(self):
        # Nudge model to reflect FS changes across platforms
        try:
            current = self.model.rootPath()
            self.model.setRootPath("")
            self.model.setRootPath(current)
        except Exception:
            pass

    def _open_index(self, idx: QModelIndex):
        if not idx.isValid():
            return
        if self.model.isDir(idx):
            # Single-click on a folder toggles expansion
            try:
                expanded = self.view.isExpanded(idx)
                self.view.setExpanded(idx, not expanded)
            except Exception:
                pass
            return
        p = self.model.filePath(idx)
        self.fileOpenRequested.emit(p)

    def _on_clicked(self, idx: QModelIndex):
        self._open_index(idx)

    def _on_activated(self, idx: QModelIndex):
        self._open_index(idx)

    def _on_double_clicked(self, idx: QModelIndex):
        self._open_index(idx)

    # ---------- Programmatic file operations ----------
    def create_file(self, path: str | Path) -> bool:
        """Create an empty file at the given path. Returns True on success."""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if p.exists():
                return False
            p.write_text("", encoding="utf-8")
            self._refresh_model()
            return True
        except Exception:
            return False

    def create_folder(self, path: str | Path) -> bool:
        """Create a folder at the given path. Returns True on success."""
        try:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=False)
            self._refresh_model()
            return True
        except Exception:
            return False

    def rename_path(self, path: str | Path, new_name: str) -> bool:
        """Rename file/folder at 'path' to 'new_name'. Returns True on success."""
        try:
            p = Path(path)
            dest = p.with_name(new_name)
            p.rename(dest)
            self._refresh_model()
            return True
        except Exception:
            return False

    def delete_path(self, path: str | Path, recursive: bool = True) -> bool:
        """Delete file or folder. If folder and recursive=True, remove recursively."""
        try:
            p = Path(path)
            if p.is_dir():
                if recursive:
                    shutil.rmtree(p)
                else:
                    p.rmdir()
            elif p.exists():
                p.unlink()
            else:
                return False
            self._refresh_model()
            return True
        except Exception:
            return False

    # ---------- Context menu UI ----------
    def _on_context_menu(self, pos: QPoint):
        index = self.view.indexAt(pos)
        base_path = Path(self.model.rootPath())
        target_path = base_path
        if index.isValid():
            try:
                fp = self.model.filePath(index)
                tp = Path(fp)
                if tp.exists():
                    target_path = tp
            except Exception:
                pass

        menu = QMenu(self)

        act_new_file = QAction("New File", self)
        act_new_folder = QAction("New Folder", self)
        act_rename = QAction("Rename", self)
        act_delete = QAction("Delete", self)

        act_new_file.triggered.connect(lambda: self._ui_new_file(target_path))
        act_new_folder.triggered.connect(lambda: self._ui_new_folder(target_path))
        act_rename.triggered.connect(lambda: self._ui_rename(target_path))
        act_delete.triggered.connect(lambda: self._ui_delete(target_path))

        menu.addAction(act_new_file)
        menu.addAction(act_new_folder)
        if target_path != base_path:
            menu.addSeparator()
            menu.addAction(act_rename)
            menu.addAction(act_delete)

        global_pos = self.view.viewport().mapToGlobal(pos)
        menu.exec(global_pos)

    def _ui_new_file(self, target: Path):
        dir_path = target if target.is_dir() else target.parent
        name, ok = QInputDialog.getText(self, "New File", "File name:")
        if not ok or not name.strip():
            return
        self.create_file(dir_path / name.strip())

    def _ui_new_folder(self, target: Path):
        dir_path = target if target.is_dir() else target.parent
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip():
            return
        self.create_folder(dir_path / name.strip())

    def _ui_rename(self, target: Path):
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=target.name)
        if not ok or not name.strip():
            return
        if not self.rename_path(target, name.strip()):
            QMessageBox.warning(self, "Rename", "Failed to rename.")

    def _ui_delete(self, target: Path):
        reply = QMessageBox.question(self, "Delete", f"Delete '{target.name}'?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if not self.delete_path(target, recursive=True):
                QMessageBox.warning(self, "Delete", "Failed to delete.")