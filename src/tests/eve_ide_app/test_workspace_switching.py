import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from src.eve_ide_app.main_window import MainWindow
from src.shell import ShellInterface


def test_open_folder_changes_root_in_same_window(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    win = MainWindow()

    # Monkeypatch the file dialog to return our temp directory
    def fake_get_existing_directory(parent, caption):
        return str(tmp_path)

    monkeypatch.setattr(
        "src.eve_ide_app.main_window.QFileDialog.getExistingDirectory",
        fake_get_existing_directory,
        raising=True,
    )

    # Track current registry state
    before = list(getattr(app, "_eve_windows", []))
    count_before = len(before)

    # Trigger Open Folder logic (now changes root in the same window)
    win._choose_folder()

    registry = getattr(app, "_eve_windows", [])
    assert len(registry) == count_before, "Open Folder should not create a new window"

    # Current window should adopt cwd/workspace_root
    assert Path(win.terminal.cwd).resolve() == tmp_path.resolve()
    assert Path(win.eve_panel.workspace_root).resolve() == tmp_path.resolve()

    # File explorer model root should update as well
    assert Path(win.file_explorer.model.rootPath()).resolve() == tmp_path.resolve()

    win.close()


def test_new_window_action_spawns_window():
    app = QApplication.instance() or QApplication([])
    win = MainWindow()

    count_before = len(getattr(app, "_eve_windows", []))
    win._open_new_window()

    registry = getattr(app, "_eve_windows", [])
    assert len(registry) == count_before + 1, "New Window action should add a window to registry"

    # Cleanup
    registry[-1].close()
    win.close()


def test_shell_uses_workspace_env_for_cwd(monkeypatch, tmp_path):
    # Ensure ShellInterface executes commands in EVE_WORKSPACE_ROOT
    monkeypatch.setenv("EVE_WORKSPACE_ROOT", str(tmp_path))

    sh = ShellInterface()
    cmd = f'"{sys.executable}" -c "import os; print(os.getcwd())"'
    out, err = sh.execute_command(cmd)

    # Normalize and compare paths
    got = Path(out.strip()).resolve()
    assert got == tmp_path.resolve(), f"Expected cwd {tmp_path}, got {got}. STDERR: {err}"