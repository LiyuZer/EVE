from __future__ import annotations
from pathlib import Path
from typing import Optional
import os

# Qt imports are local to functions to avoid import side-effects in environments
# where Qt may not be available or a display server is missing.


def _project_root() -> Path:
    # src/eve_ide_app/splash.py -> parents[2] is project root
    return Path(__file__).resolve().parents[2]


def get_logo_path() -> Optional[Path]:
    """Return a best-effort path to the Eve dragon logo image if present.

    Checks canonical assets first, then falls back to project-root copies.
    """
    module_root = Path(__file__).resolve().parent
    candidates = [
        module_root / "assets" / "logo" / "logo.jpg",
        module_root / "assets" / "logo" / "eve-dragon.jpg",
        _project_root() / "src" / "eve_ide_app" / "assets" / "logo" / "logo.jpg",
        _project_root() / "src" / "eve_ide_app" / "assets" / "logo" / "eve-dragon.jpg",
        _project_root() / "src" / "Eve.jpg",  # additional fallback present in repo
        _project_root() / "eve-logo.jpg",
        _project_root() / "eve-logo1.jpg",
    ]
    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            continue
    return None


def _env_truthy(var: str, default: str | None = None) -> bool:
    v = os.environ.get(var, default) or ""
    v = v.strip().lower()
    return v in {"1", "true", "on", "yes"}


def _env_falsey(var: str, default: str | None = None) -> bool:
    v = os.environ.get(var, default) or ""
    v = v.strip().lower()
    return v in {"0", "false", "off", "no"}


def _env_int(var: str, default: int | None = None) -> int | None:
    try:
        v = os.environ.get(var, None)
        if v is None:
            return default
        return int(str(v).strip())
    except Exception:
        return default


def _env_float(var: str, default: float | None = None) -> float | None:
    try:
        v = os.environ.get(var, None)
        if v is None:
            return default
        return float(str(v).strip())
    except Exception:
        return default


def should_show_splash() -> bool:
    """Determine if splash should be shown.

    Disabled when:
    - QT_QPA_PLATFORM is 'offscreen' (tests/CI)
    - EVE_SPLASH is set to a falsey value (0/false/off/no)
    - Running under pytest (PYTEST_CURRENT_TEST set) or CI env

    Overrides:
    - EVE_SPLASH_FORCE=true will force-enable the splash regardless of CI/pytest,
      but still respects QT_QPA_PLATFORM=offscreen to avoid UI in headless mode.
    """
    platform = (os.environ.get("QT_QPA_PLATFORM") or "").strip().lower()
    if platform == "offscreen":
        return False

    # Force-enable if requested (except in true offscreen mode)
    if _env_truthy("EVE_SPLASH_FORCE"):
        return True

    if _env_falsey("EVE_SPLASH"):
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    if _env_truthy("CI"):
        # In CI, be conservative
        return False
    return True


def maybe_show_splash(app, duration_ms: int = 1200):
    """Show a non-blocking splash screen if allowed, returning the splash.

    Returns None if splash is suppressed (tests/CI/offscreen) or if assets are missing.
    The caller may call splash.finish(main_window) after showing the main window.
    Regardless, the splash auto-closes after duration_ms to avoid lingering.

    Environment variables:
    - EVE_SPLASH_FORCE:       If truthy, force-enable showing splash (except offscreen)
    - EVE_SPLASH_DURATION_MS: Custom duration in ms (min 300ms)
    - EVE_SPLASH_MAX_WH:      Max width/height in px for the splash (single int)
    - EVE_SPLASH_SIZE_PCT:    Desired size as fraction or percent of the smaller screen
                              dimension (e.g., 0.35 or 35 for 35%). Overrides MAX_WH.
    """
    try:
        if not should_show_splash():
            return None
        logo = get_logo_path()
        if not logo:
            return None
        # Lazy import to keep module import side-effect free
        from PySide6.QtWidgets import QSplashScreen
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt, QTimer

        # Duration override from env
        env_ms = _env_int("EVE_SPLASH_DURATION_MS", None)
        if env_ms is not None:
            try:
                duration_ms = max(300, int(env_ms))
            except Exception:
                pass

        pix = QPixmap(str(logo))
        if pix.isNull():
            return None

        # Determine target size: prefer SIZE_PCT if provided, else cap with MAX_WH
        size_pct = os.environ.get("EVE_SPLASH_SIZE_PCT", "").strip()
        if size_pct:
            f = None
            try:
                f = float(size_pct)
                if f > 1.0:
                    # Treat as percent if value > 1
                    f = f / 100.0
                # clamp reasonable range
                f = max(0.05, min(1.0, f))
            except Exception:
                f = None
            if f:
                try:
                    screen = getattr(app, "primaryScreen", lambda: None)() or (app.screens()[0] if getattr(app, "screens", lambda: [])() else None)
                    if screen is not None:
                        geo = screen.availableGeometry()
                        target = int(min(geo.width(), geo.height()) * f)
                        if target > 0:
                            pix = pix.scaled(target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                except Exception:
                    pass
        else:
            # Max-capped scaling for large images
            max_wh = _env_int("EVE_SPLASH_MAX_WH", None)
            if max_wh is None:
                max_w, max_h = 640, 640
            else:
                max_w = max_h = int(max_wh)
            if pix.width() > max_w or pix.height() > max_h:
                pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        splash = QSplashScreen(pix)
        # Keep above all; frameless looks cleaner for a splash
        try:
            splash.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            splash.setWindowFlag(Qt.FramelessWindowHint, True)
        except Exception:
            pass

        splash.show()

        # Center on primary screen after showing
        try:
            screen = getattr(app, "primaryScreen", lambda: None)() or (app.screens()[0] if getattr(app, "screens", lambda: [])() else None)
            if screen is not None:
                geo = screen.availableGeometry()
                x = geo.x() + (geo.width() - pix.width()) // 2
                y = geo.y() + (geo.height() - pix.height()) // 2
                splash.move(int(x), int(y))
        except Exception:
            pass

        # Ensure it goes away automatically
        QTimer.singleShot(int(duration_ms), splash.close)
        # Process events so it paints immediately
        try:
            app.processEvents()
        except Exception:
            pass
        return splash
    except Exception:
        return None