import re
from eve_ide_app.themes import get_syntax_palette, SYNTAX_PALETTE_KEYS


def _is_hex_color(s: str) -> bool:
    return bool(re.fullmatch(r"#[0-9a-fA-F]{6}", s))


def test_palette_has_required_keys():
    themes = ["eve", "dragon", "neon", "light"]
    for name in themes:
        pal = get_syntax_palette(name)
        # Must contain all required keys
        for k in SYNTAX_PALETTE_KEYS:
            assert k in pal, f"{name} palette missing key: {k}"


def test_palette_values_are_hex():
    themes = ["eve", "dragon", "neon", "light"]
    for name in themes:
        pal = get_syntax_palette(name)
        for k, v in pal.items():
            assert _is_hex_color(v), f"{name}:{k} has non-hex value: {v}"


def test_theme_fallback_default():
    pal_unknown = get_syntax_palette("unknown_eve_theme")
    pal_eve = get_syntax_palette("eve")
    assert pal_unknown == pal_eve, "Unknown theme should fall back to 'eve' palette"
