from __future__ import annotations

import os
import shlex
from pathlib import Path

import pytest

from src.eve_session import EveSession


@pytest.fixture
def session_in_tmp(monkeypatch, tmp_path: Path):
    # Pin workspace root to tmp so EveSession uses it as repo_root
    monkeypatch.setenv("EVE_WORKSPACE_ROOT", str(tmp_path))
    s = EveSession()
    s.ensure(reset=True)
    return s


def _read_lines(p: Path) -> list[str]:
    return p.read_text(encoding="utf-8").splitlines()


def test_ensure_and_reset_creates_session(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EVE_WORKSPACE_ROOT", str(tmp_path))
    s = EveSession()
    s.ensure(reset=True)

    assert s.session_file.exists()
    text = s.session_file.read_text(encoding="utf-8")
    assert f"cd {shlex.quote(str(tmp_path))}" in text


def test_update_cd_inside_repo(session_in_tmp: EveSession, tmp_path: Path):
    s = session_in_tmp
    sub = tmp_path / "foo"
    sub.mkdir()

    ok, msg = s.update_cd("foo")
    assert ok is True
    assert "cwd set to" in msg.lower()
    assert s.current_cwd() == sub.resolve()

    # Now go back up one directory using ..
    ok, msg = s.update_cd("..")
    assert ok is True
    assert s.current_cwd() == tmp_path.resolve()


def test_update_cd_outside_rejected(session_in_tmp: EveSession, tmp_path: Path):
    s = session_in_tmp
    outside = tmp_path.parent
    # Ensure outside exists and is dir (it should)
    assert outside.exists() and outside.is_dir()

    ok, msg = s.update_cd(str(outside))
    assert ok is False
    assert "outside workspace" in msg.lower()
    # cwd stays within repo root
    assert s.current_cwd() == tmp_path.resolve()


def test_export_and_unset_idempotent(session_in_tmp: EveSession):
    s = session_in_tmp

    ok, _ = s.export("FOO", "a b c")
    assert ok is True
    lines = _read_lines(s.session_file)
    assert any(ln.strip().startswith("export FOO=") for ln in lines)

    # Re-export overrides prior line (idempotent)
    ok, _ = s.export("FOO", "xyz")
    assert ok is True
    lines = _read_lines(s.session_file)
    exports = [ln for ln in lines if ln.strip().startswith("export FOO=")]
    assert len(exports) == 1
    assert exports[0].strip() == f"export FOO={shlex.quote('xyz')}"

    # Unset removes export and adds unset
    ok, _ = s.unset("FOO")
    assert ok is True
    lines = _read_lines(s.session_file)
    assert not any(ln.strip().startswith("export FOO=") for ln in lines)
    assert any(ln.strip() == "unset FOO" for ln in lines)

    # Invalid var names are rejected
    ok, msg = s.export("1BAD", "v")
    assert ok is False and "invalid" in msg.lower()
    ok, msg = s.unset("1BAD")
    assert ok is False and "invalid" in msg.lower()


def test_source_and_compose_helpers(session_in_tmp: EveSession):
    s = session_in_tmp
    src = s.source_command()
    assert str(s.session_file) in src
    assert "[ -f" in src and "." in src  # simple sanity

    composed = s.compose_prefixed("echo hello")
    assert src in composed
    assert composed.strip().endswith("echo hello")
