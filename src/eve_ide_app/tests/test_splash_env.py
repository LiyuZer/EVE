import os
import sys
from pathlib import Path
import importlib

# Ensure project root and src are on sys.path regardless of where pytest is run
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[3]  # .../src/eve_ide_app/tests/test_splash_env.py -> project root
SRC_DIR = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import src.eve_ide_app.splash as splash  # noqa: E402


def test_should_show_splash_offscreen_false(monkeypatch):
    # Offscreen should always disable splash regardless of other envs
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.delenv("EVE_SPLASH_FORCE", raising=False)
    monkeypatch.delenv("EVE_SPLASH", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert splash.should_show_splash() is False


def test_force_true_overrides_ci_and_pytest(monkeypatch):
    # Force flag should enable splash even if CI/pytest are set (as long as not offscreen)
    monkeypatch.setenv("QT_QPA_PLATFORM", "cocoa")  # any non-offscreen platform
    monkeypatch.setenv("EVE_SPLASH_FORCE", "1")
    monkeypatch.setenv("CI", "1")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "dummy")
    assert splash.should_show_splash() is True


def test_falsey_env_disables(monkeypatch):
    # Explicit falsey EVE_SPLASH disables the splash
    monkeypatch.setenv("QT_QPA_PLATFORM", "")
    monkeypatch.setenv("EVE_SPLASH", "0")
    monkeypatch.delenv("EVE_SPLASH_FORCE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert splash.should_show_splash() is False


def test_default_true_when_not_offscreen(monkeypatch):
    # With no restricting envs and not offscreen, splash should show
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("EVE_SPLASH", raising=False)
    monkeypatch.delenv("EVE_SPLASH_FORCE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert splash.should_show_splash() is True


def test_get_logo_path_exists():
    p = splash.get_logo_path()
    # The repo includes assets/logo/logo.jpg; ensure we find a real image
    assert p is not None and p.exists(), "Expected a logo image to exist for splash"
