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
MAX_SLIDE_BULLETS = 6    # max total bullet/list items across the whole slide


def count_bullet_items(text: str) -> int:
    """Count bullet points or numbered list items in *text*."""
    if not text:
        return 0
    pattern = re.compile(
        r"^\s*(?:[•\-*+→]|\d+[\.\)]|[a-zA-Z][\.\)])\s*\S+"
    )
    return sum(1 for line in text.splitlines() if pattern.match(line))


def analyze_element_content(text: str) -> Tuple[int, int, int]:
    """Return *(line_count, char_count, bullet_count)* for an element's text."""
    if not text:
        return 0, 0, 0
    lines = text.splitlines()
    return len(lines), len(text), count_bullet_items(text)
