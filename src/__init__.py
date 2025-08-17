"""
Package initializer for src.
Re-exports accepts() from target_parser when available.
"""
try:
    from .target_parser import accepts  # noqa: F401
except Exception:
    # target_parser may not exist yet; safe to ignore
    pass
