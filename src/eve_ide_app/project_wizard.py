from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
)


class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('New Project')
        self.name_edit = QLineEdit(self)
        self.dir_edit = QLineEdit(self)
        browse = QPushButton('Browse…', self)
        browse.clicked.connect(self._browse)

        form = QVBoxLayout(self)
        row1 = QHBoxLayout(); row1.addWidget(QLabel('Name:')); row1.addWidget(self.name_edit)
        row2 = QHBoxLayout(); row2.addWidget(QLabel('Location:')); row2.addWidget(self.dir_edit); row2.addWidget(browse)
        form.addLayout(row1); form.addLayout(row2)
        btns = QHBoxLayout(); ok = QPushButton('Create'); cancel = QPushButton('Cancel')
        ok.clicked.connect(self.accept); cancel.clicked.connect(self.reject)
        btns.addStretch(1); btns.addWidget(ok); btns.addWidget(cancel)
        form.addLayout(btns)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, 'Choose Location')
        if d:
            self.dir_edit.setText(d)

    def result_path(self) -> Path | None:
        name = self.name_edit.text().strip()
        base = Path(self.dir_edit.text().strip()) if self.dir_edit.text().strip() else None
        if not name or not base:
            return None
        return (base / name)

    @staticmethod
    def create_basic_project(path: Path) -> bool:
        try:
            path.mkdir(parents=True, exist_ok=False)
            (path / 'README.md').write_text(f"# {path.name}\n\nCreated by Eve IDE.\n")
            (path / 'requirements.txt').write_text("")
            (path / 'main.py').write_text("if __name__ == '__main__':\n    print('Hello from new project!')\n")
            return True
        except Exception:
            return False
