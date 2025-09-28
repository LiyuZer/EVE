#!/usr/bin/env python3
"""
Lightweight CLI UI utilities (minimal, Claude-style aesthetic):
- ASCII-only, readable, NO_COLOR/TTY-aware via shared styler
- Section headers
- Aligned ASCII tables
- Simple progress context manager with optional spinner

Usage:
    from src.cli.ui import section, print_section, table, print_table, progress
    from src.cli.style import styler

    print_section("Startup")
    print(styler.tag("info", "info"), "Initializing...")

    cols = ["Step", "Status", "Time"]
    rows = [["Scan", "ok", "0.8s"], ["Build", "ok", "3.2s"]]
    print_table(cols, rows)

    with progress("Analyzing repository") as p:
        # ... do work
        p.update("indexing")
"""
from __future__ import annotations

import sys
import time
import shutil
import threading
from contextlib import contextmanager
from typing import Iterable, List, Sequence

from src.cli.style import styler


# ---------- Section headers ----------

def section(title: str, ch: str = "-") -> str:
    """Return a styled section header string."""
    top = styler.header(title, ch=ch)
    return top


def print_section(title: str, ch: str = "-") -> None:
    print(section(title, ch=ch))


# ---------- Tables (ASCII, aligned) ----------

def _to_str_grid(rows: Iterable[Sequence[object]]) -> List[List[str]]:
    grid: List[List[str]] = []
    for r in rows:
        grid.append(["" if x is None else str(x) for x in r])
    return grid


def table(columns: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """Build an aligned ASCII table with a dashed separator after the header."""
    cols = list(columns)
    data = _to_str_grid(rows)

    # Compute column widths
    widths = [len(str(c)) for c in cols]
    for r in data:
        for i, cell in enumerate(r):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))
            else:
                widths.append(len(cell))

    # Row builders
    def fmt_row(items: Sequence[str]) -> str:
        cells = []
        for i, val in enumerate(items):
            w = widths[i]
            cells.append(val.ljust(w))
        return " | ".join(cells)

    # Build table parts
    head = fmt_row([str(c) for c in cols])
    sep = "-+-".join("-" * w for w in widths)
    body = "\n".join(fmt_row(r) for r in data)

    # Apply subtle dim style to separator
    sep = styler.apply(styler.palette.dim, sep)

    if body:
        return f"{head}\n{sep}\n{body}"
    else:
        return f"{head}\n{sep}"


def print_table(columns: Sequence[str], rows: Iterable[Sequence[object]]) -> None:
    print(table(columns, rows))


# ---------- Progress (spinner + timing) ----------

class _ProgressState:
    def __init__(self, text: str) -> None:
        self.text = text
        self._lock = threading.Lock()
        self._running = False
        self._msg = text
        self._thread: threading.Thread | None = None
        self._start = time.time()

    def start(self) -> None:
        self._running = True
        if sys.stdout.isatty():
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            # Non-TTY: print a single start line
            print(styler.tag("run", "info"), self.text)

    def _spin(self) -> None:
        frames = "-\\|/"
        i = 0
        while self._running:
            with self._lock:
                msg = self._msg
            line = f"{styler.tag('run', 'info')} {msg} {frames[i % len(frames)]}"
            # Carriage return spinner; avoid newline until stop
            print(line, end="\r", flush=True)
            i += 1
            time.sleep(0.08)

    def update(self, msg: str) -> None:
        with self._lock:
            self._msg = msg

    def stop(self, ok: bool, err: Exception | None = None) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.25)
        dur = time.time() - self._start
        tag = styler.tag("ok", "success") if ok else styler.tag("error", "error")
        base = self._msg if self._msg else self.text
        # Clear spinner line if TTY
        if sys.stdout.isatty():
            cols = shutil.get_terminal_size(fallback=(80, 24)).columns
            print(" " * max(0, cols - 1), end="\r")
        if ok:
            print(f"{tag} {base} ({dur:.1f}s)")
        else:
            out = f"{tag} {base} ({dur:.1f}s)"
            if err is not None:
                out += f" - {err}"
            print(out)


@contextmanager
def progress(text: str):
    """Context manager for simple progress reporting with timing and optional spinner.

    Example:
        with progress("Fetching data") as p:
            p.update("connecting")
            ...
    """
    st = _ProgressState(text)
    st.start()
    try:
        yield st
        st.stop(ok=True)
    except Exception as e:
        st.stop(ok=False, err=e)
        raise
