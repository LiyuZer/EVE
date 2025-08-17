import os
from pathlib import Path

import pytest

from src.eve_session import EveSession
from src.eve_ide_app.terminal_widget import handle_cd


def test_cd_persists_across_venv_activation(tmp_path, monkeypatch):
    # Create isolated workspace and point EveSession there
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setenv("EVE_WORKSPACE_ROOT", str(root))

    s = EveSession()
    s.reset()  # ensures session file with default cd to root

    assert s.current_cwd() == root

    # Change cwd to a subdir and ensure persisted
    subdir = root / "sub"
    subdir.mkdir()
    ok, msg = s.update_cd(str(subdir))
    assert ok, msg
    assert s.current_cwd() == subdir

    # Create a fake venv structure and activate it
    venv = root / ".venv"
    (venv / "bin").mkdir(parents=True)
    # Create a dummy python executable marker
    (venv / "bin" / "python").write_text("", encoding="utf-8")

    ok, msg = s.activate_venv(venv)
    assert ok, msg

    # CWD should remain the same after venv activation
    assert s.current_cwd() == subdir

    # Session file should still contain a cd line and the new exports
    text = s.session_file.read_text(encoding="utf-8")
    assert any(ln.strip().startswith("cd ") for ln in text.splitlines())
    assert any(ln.strip().startswith("export VIRTUAL_ENV=") for ln in text.splitlines())
    assert any(ln.strip().startswith("export PATH=") and "$VIRTUAL_ENV" in ln for ln in text.splitlines())

    # Deactivate and ensure cwd is still stable
    ok, msg = s.deactivate_venv()
    assert ok, msg
    assert s.current_cwd() == subdir


def test_source_command_is_absolute(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    root.mkdir()
    monkeypatch.setenv("EVE_WORKSPACE_ROOT", str(root))

    s = EveSession()
    s.reset()
    cmd = s.source_command()
    # Should reference the absolute session file path
    assert str(s.session_file) in cmd
    assert cmd.startswith("[ -f ")


def test_handle_cd_quotes_and_messages(tmp_path):
    base = tmp_path
    target = base / "a b"
    target.mkdir()

    handled, new_cwd, to_send, msg = handle_cd(base, "cd a b")
    assert handled
    assert new_cwd == target
    # Ensure correct quoting for a path with spaces (POSIX single quotes)
    if os.name != "nt":
        assert to_send.startswith("cd '") and to_send.endswith("'")
    else:
        assert to_send.startswith('cd "') and to_send.endswith('"')
    assert "cwd set to" in msg
