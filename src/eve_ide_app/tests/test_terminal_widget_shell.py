import os
import sys
import shutil
from pathlib import Path
import pytest

# We will add choose_shell and handle_cd in terminal_widget.py
# Tests are written first to drive implementation.

def import_module():
    import importlib
    mod = importlib.import_module('src.eve_ide_app.terminal_widget')
    return mod


def test_choose_shell_env_zsh(monkeypatch):
    mod = import_module()
    # Simulate POSIX
    monkeypatch.setattr(sys, 'platform', 'darwin', raising=False)
    # SHELL points to zsh and is executable
    monkeypatch.setenv('SHELL', '/bin/zsh')
    monkeypatch.setattr(mod.os.path, 'isfile', lambda p: p == '/bin/zsh')
    monkeypatch.setattr(mod.os, 'access', lambda p, m: p == '/bin/zsh')

    program, args = mod.choose_shell()

    assert program.endswith('zsh') or program == '/bin/zsh'
    assert '-i' in args


def test_choose_shell_no_env_prefers_zsh_bash_sh(monkeypatch):
    mod = import_module()
    monkeypatch.setattr(sys, 'platform', 'linux', raising=False)
    monkeypatch.delenv('SHELL', raising=False)

    # Present only bash and sh -> expect zsh if available, then bash, else sh
    order = {'zsh': '/usr/bin/zsh', 'bash': '/usr/bin/bash', 'sh': '/bin/sh'}
    monkeypatch.setattr(mod.shutil, 'which', lambda name: order.get(name))

    program, args = mod.choose_shell()
    assert program.endswith('zsh')
    assert '-i' in args

    # If zsh missing, prefer bash
    monkeypatch.setattr(mod.shutil, 'which', lambda name: {'bash': '/usr/bin/bash', 'sh': '/bin/sh'}.get(name))
    program, args = mod.choose_shell()
    assert program.endswith('bash')
    assert '-i' in args

    # If only sh, fall back to sh
    monkeypatch.setattr(mod.shutil, 'which', lambda name: {'sh': '/bin/sh'}.get(name))
    program, args = mod.choose_shell()
    assert program.endswith('sh')
    assert '-i' in args


def test_choose_shell_windows_prefers_powershell(monkeypatch):
    mod = import_module()
    monkeypatch.setattr(sys, 'platform', 'win32', raising=False)
    monkeypatch.delenv('SHELL', raising=False)

    def fake_which(name):
        if name.lower() in ('powershell', 'pwsh', 'powershell.exe'):  # emulate powershell available
            return r'C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe'
        if name.lower() in ('cmd', 'cmd.exe'):
            return r'C:\\Windows\\System32\\cmd.exe'
        return None

    monkeypatch.setattr(mod.shutil, 'which', fake_which)

    program, args = mod.choose_shell()
    assert 'powershell' in program.lower()
    assert args == []

    # If no powershell, fallback to cmd
    def fake_which_cmd_only(name):
        if name.lower() in ('cmd', 'cmd.exe'):
            return r'C:\\Windows\\System32\\cmd.exe'
        return None

    monkeypatch.setattr(mod.shutil, 'which', fake_which_cmd_only)
    program, args = mod.choose_shell()
    assert program.lower().endswith('cmd.exe') or program.lower().endswith('cmd')
    assert args == []


def test_handle_cd_existing(tmp_path: Path):
    mod = import_module()
    base = tmp_path
    sub = base / 'foo'
    sub.mkdir()

    handled, new_cwd, to_send, message = mod.handle_cd(base, f'cd {sub.name}')

    assert handled is True
    assert new_cwd == sub
    assert to_send.startswith('cd ')
    assert str(sub) in to_send
    assert 'cwd set to' in message.lower()


def test_handle_cd_missing(tmp_path: Path):
    mod = import_module()
    base = tmp_path

    handled, new_cwd, to_send, message = mod.handle_cd(base, 'cd nosuchdir')

    assert handled is True
    assert new_cwd == base  # unchanged
    assert to_send == ''
    assert 'no such' in message.lower()


def test_handle_cd_home(monkeypatch, tmp_path):
    mod = import_module()
    home = tmp_path / 'homeuser'
    home.mkdir()
    monkeypatch.setenv('HOME', str(home))

    # cd with no args
    handled, new_cwd, to_send, message = mod.handle_cd(tmp_path, 'cd')
    assert handled is True
    assert new_cwd == home
    assert str(home) in to_send

    # cd ~
    handled, new_cwd, to_send, message = mod.handle_cd(tmp_path, 'cd ~')
    assert handled is True
    assert new_cwd == home
    assert str(home) in to_send
