import re

_ANSI_RE = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")

def strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s or "")


def truncate_middle(s: str, max_len: int, ellipsis: str = "…") -> str:
    if max_len <= 0:
        return ""
    if s is None:
        return ""
    if len(s) <= max_len:
        return s
    if max_len <= len(ellipsis):
        return ellipsis[:max_len]
    avail = max_len - len(ellipsis)
    head = (avail + 1) // 2
    tail = avail - head
    return s[:head] + ellipsis + s[-tail:] if tail > 0 else s[:head] + ellipsis
