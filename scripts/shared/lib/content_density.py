"""
shared/lib/content_density.py

Pure content-density evaluation helpers extracted from lint_slide.py.
All functions are side-effect-free (no I/O) for easy unit testing.
"""
import re
from typing import Tuple

# ---------------------------------------------------------------------------
# Threshold constants — single source of truth used by lint_slide.py
# ---------------------------------------------------------------------------
MAX_ELEM_LINES   = 5     # max lines in a single text element
MAX_ELEM_CHARS   = 200   # max characters in a single text element
MAX_SLIDE_CHARS  = 480   # max total characters across the whole slide
MAX_SLIDE_BULLETS = 3    # max total bullet/list items across the whole slide


def count_bullet_items(text: str) -> int:
    """Count bullet points or numbered list items in *text*."""
    if not text:
        return 0
    pattern = re.compile(
        r"^\s*(?:[•\-*+→]|\d+[\.\)]|[a-zA-Z][\.\)])\s*\S+"
    )
    return sum(1 for line in text.splitlines() if pattern.match(line))


def count_json_content_items(obj: object) -> int:
    """Recursively count discrete bullet/content items inside a JSON object or array."""
    if obj is None:
        return 0
    if isinstance(obj, str):
        if not obj.strip():
            return 0
        bullets = count_bullet_items(obj)
        return bullets if bullets > 0 else 1
    if isinstance(obj, (int, float, bool)):
        return 1
    if isinstance(obj, list):
        if not obj:
            return 0
        return sum(count_json_content_items(item) for item in obj)
    if isinstance(obj, dict):
        if not obj:
            return 0
        # If all dict values are primitive (strings/numbers/bools), it's 1 discrete structured record
        if all(not isinstance(v, (list, dict)) for v in obj.values()):
            return 1
        # Otherwise, sum item counts across nested lists/dicts
        total = 0
        for val in obj.values():
            total += count_json_content_items(val)
        return total
    return 0


def analyze_element_content(text: str) -> Tuple[int, int, int]:
    """Return *(line_count, char_count, bullet_count)* for an element's text."""
    if not text:
        return 0, 0, 0
    lines = text.splitlines()
    return len(lines), len(text), count_bullet_items(text)

