#!/usr/bin/env python3
"""
Central CLI style helpers for a minimal, readable aesthetic (Claude Code vibe):
- Cyan accent by default
- Respects NO_COLOR and non-TTY (falls back to plain text)
- Lightweight utilities: tag(), divider(), header(), color application

Usage:
    from src.cli.style import styler
    print(styler.header("EVE CLI v0.1"))
    print(styler.tag("run", "info"), "Analyzing repository...")
"""
from __future__ import annotations

import os
import sys
import shutil
from dataclasses import dataclass
import colorama

colorama.init()


def is_color_enabled() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    try:
        return sys.stdout.isatty()
    except Exception:
        return False


@dataclass(frozen=True)
class Palette:
    accent: str
    info: str
    success: str
    warn: str
    error: str
    dim: str
    reset: str


DEFAULT_PALETTE = Palette(
    accent=colorama.Fore.CYAN + colorama.Style.BRIGHT,
    info=colorama.Fore.CYAN,
    success=colorama.Fore.GREEN + colorama.Style.BRIGHT,
    warn=colorama.Fore.YELLOW + colorama.Style.BRIGHT,
    error=colorama.Fore.RED + colorama.Style.BRIGHT,
    dim=colorama.Fore.WHITE + colorama.Style.DIM,
    reset=colorama.Style.RESET_ALL,
)


class Styler:
    def __init__(self, palette: Palette = DEFAULT_PALETTE, enabled: bool | None = None) -> None:
        self.palette = palette
        self.enabled = is_color_enabled() if enabled is None else enabled

    def apply(self, color_code: str, text: str) -> str:
        if self.enabled and color_code:
            return f"{color_code}{text}{self.palette.reset}"
        return text

    def tag(self, name: str, kind: str = "accent") -> str:
        color = getattr(self.palette, kind, self.palette.accent)
        left = self.apply(self.palette.dim, "[")
        right = self.apply(self.palette.dim, "]")
        return f"{left}{self.apply(color, name)}{right}"

    def divider(self, ch: str = "-", width: int | None = None) -> str:
        cols = shutil.get_terminal_size(fallback=(80, 24)).columns
        w = max(20, min(cols, width or cols))
        return ch * w

    def header(self, title: str, ch: str = "-") -> str:
        line = self.divider(ch=ch)
        t = f" {title.strip()} "
        return f"{self.apply(self.palette.accent, t)}\n{self.apply(self.palette.dim, line)}"


# Shared singleton
styler = Styler()
