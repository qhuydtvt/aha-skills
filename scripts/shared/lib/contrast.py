"""WCAG 2.1 Color Contrast calculation and evaluation utilities."""

import re
from typing import Any

# Common CSS named colors map (normalized 0.0 - 1.0 sRGB)
NAMED_COLORS: dict[str, tuple[float, float, float, float]] = {
    "black": (0.0, 0.0, 0.0, 1.0),
    "white": (1.0, 1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0, 1.0),
    "lime": (0.0, 1.0, 0.0, 1.0),
    "blue": (0.0, 0.0, 1.0, 1.0),
    "yellow": (1.0, 1.0, 0.0, 1.0),
    "cyan": (0.0, 1.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0, 1.0),
    "silver": (0.753, 0.753, 0.753, 1.0),
    "gray": (0.502, 0.502, 0.502, 1.0),
    "grey": (0.502, 0.502, 0.502, 1.0),
    "maroon": (0.5, 0.0, 0.0, 1.0),
    "olive": (0.5, 0.5, 0.0, 1.0),
    "green": (0.0, 0.5, 0.0, 1.0),
    "purple": (0.5, 0.0, 0.5, 1.0),
    "teal": (0.0, 0.5, 0.5, 1.0),
    "navy": (0.0, 0.0, 0.5, 1.0),
    "transparent": (0.0, 0.0, 0.0, 0.0),
    "none": (0.0, 0.0, 0.0, 0.0),
}


def parse_color(color_val: Any) -> tuple[float, float, float, float]:
    """Parse color string (hex, rgb, rgba, named) or tuple into RGBA floats (0.0 - 1.0).

    Args:
        color_val: Hex string (e.g., "#fff", "#1e293b", "rgba(0,0,0,0.5)"), named color, or tuple.

    Returns:
        tuple[float, float, float, float]: Normalized (r, g, b, alpha) in 0.0 - 1.0.
    """
    if isinstance(color_val, (tuple, list)):
        if len(color_val) == 3:
            return (float(color_val[0]), float(color_val[1]), float(color_val[2]), 1.0)
        elif len(color_val) >= 4:
            return (float(color_val[0]), float(color_val[1]), float(color_val[2]), float(color_val[3]))
        return (0.0, 0.0, 0.0, 1.0)

    if not color_val or not isinstance(color_val, str):
        return (0.0, 0.0, 0.0, 1.0)

    s = color_val.strip().lower()

    if s in NAMED_COLORS:
        return NAMED_COLORS[s]

    # Hex matching: #rgb, #rgba, #rrggbb, #rrggbbaa
    if s.startswith("#"):
        hex_str = s[1:]
        if len(hex_str) == 3:  # #rgb
            r = int(hex_str[0] * 2, 16) / 255.0
            g = int(hex_str[1] * 2, 16) / 255.0
            b = int(hex_str[2] * 2, 16) / 255.0
            return (r, g, b, 1.0)
        elif len(hex_str) == 4:  # #rgba
            r = int(hex_str[0] * 2, 16) / 255.0
            g = int(hex_str[1] * 2, 16) / 255.0
            b = int(hex_str[2] * 2, 16) / 255.0
            a = int(hex_str[3] * 2, 16) / 255.0
            return (r, g, b, a)
        elif len(hex_str) == 6:  # #rrggbb
            r = int(hex_str[0:2], 16) / 255.0
            g = int(hex_str[2:4], 16) / 255.0
            b = int(hex_str[4:6], 16) / 255.0
            return (r, g, b, 1.0)
        elif len(hex_str) == 8:  # #rrggbbaa
            r = int(hex_str[0:2], 16) / 255.0
            g = int(hex_str[2:4], 16) / 255.0
            b = int(hex_str[4:6], 16) / 255.0
            a = int(hex_str[6:8], 16) / 255.0
            return (r, g, b, a)

    # rgb(...) / rgba(...) matching
    rgba_match = re.match(
        r"^rgba?\(\s*([\d\.]+)\s*,\s*([\d\.]+)\s*,\s*([\d\.]+)(?:\s*,\s*([\d\.]+))?\s*\)$",
        s,
    )
    if rgba_match:
        r = float(rgba_match.group(1)) / 255.0 if float(rgba_match.group(1)) > 1.0 else float(rgba_match.group(1))
        g = float(rgba_match.group(2)) / 255.0 if float(rgba_match.group(2)) > 1.0 else float(rgba_match.group(2))
        b = float(rgba_match.group(3)) / 255.0 if float(rgba_match.group(3)) > 1.0 else float(rgba_match.group(3))
        a = float(rgba_match.group(4)) if rgba_match.group(4) is not None else 1.0
        return (max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)), max(0.0, min(1.0, a)))

    return (0.0, 0.0, 0.0, 1.0)


def blend_colors(
    fg_rgba: tuple[float, float, float, float],
    bg_rgba: tuple[float, float, float, float],
) -> tuple[float, float, float]:
    """Alpha composite foreground color over background color.

    Returns:
        tuple[float, float, float]: Opaque RGB tuple (0.0 - 1.0).
    """
    r_f, g_f, b_f, a_f = fg_rgba
    r_b, g_b, b_b, a_b = bg_rgba

    r_out = a_f * r_f + (1.0 - a_f) * r_b
    g_out = a_f * g_f + (1.0 - a_f) * g_b
    b_out = a_f * b_f + (1.0 - a_f) * b_b

    return (r_out, g_out, b_out)


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    """Calculate WCAG 2.1 relative luminance for an RGB tuple (0.0 - 1.0)."""
    def linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r_lin = linearize(max(0.0, min(1.0, rgb[0])))
    g_lin = linearize(max(0.0, min(1.0, rgb[1])))
    b_lin = linearize(max(0.0, min(1.0, rgb[2])))

    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def contrast_ratio(
    fg_val: Any,
    bg_val: Any,
    canvas_bg_val: Any = "#ffffff",
) -> float:
    """Calculate WCAG 2.1 relative contrast ratio between foreground and background colors.

    Args:
        fg_val: Foreground text color.
        bg_val: Container or backdrop color.
        canvas_bg_val: Fallback canvas background color if bg_val is semi-transparent.

    Returns:
        float: Contrast ratio in range [1.0, 21.0].
    """
    canvas_rgba = parse_color(canvas_bg_val)
    bg_rgba = parse_color(bg_val)
    fg_rgba = parse_color(fg_val)

    # Composite background over canvas if background has alpha
    effective_bg_rgb = blend_colors(bg_rgba, canvas_rgba)

    # Composite foreground over effective background if foreground has alpha
    effective_fg_rgb = blend_colors(fg_rgba, (effective_bg_rgb[0], effective_bg_rgb[1], effective_bg_rgb[2], 1.0))

    l_fg = relative_luminance(effective_fg_rgb)
    l_bg = relative_luminance(effective_bg_rgb)

    l1 = max(l_fg, l_bg)
    l2 = min(l_fg, l_bg)

    return (l1 + 0.05) / (l2 + 0.05)


def evaluate_contrast(
    fg_val: Any,
    bg_val: Any,
    canvas_bg_val: Any = "#ffffff",
    is_large_text: bool = False,
    level: str = "AA",
) -> dict[str, Any]:
    """Evaluate contrast ratio against WCAG 2.1 AA/AAA compliance thresholds.

    Args:
        fg_val: Foreground text color.
        bg_val: Background container/canvas color.
        canvas_bg_val: Base canvas color.
        is_large_text: True if text >= 24px (18pt) or >= 18.66px (14pt) bold.
        level: "AA" or "AAA".

    Returns:
        dict[str, Any]: Evaluation result containing ratio, pass status, and min required ratio.
    """
    ratio = contrast_ratio(fg_val, bg_val, canvas_bg_val=canvas_bg_val)

    if level.upper() == "AAA":
        required = 4.5 if is_large_text else 7.0
    else:  # AA default
        required = 3.0 if is_large_text else 4.5

    is_pass = ratio >= required

    return {
        "ratio": round(ratio, 2),
        "pass": is_pass,
        "required": required,
        "level": level.upper(),
        "is_large_text": is_large_text,
    }
