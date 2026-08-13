from __future__ import annotations
"""Shared helper library package."""

from scripts.shared.lib.layout_padding import (
    calculate_inner_padding,
    calculate_slide_margins,
    is_contained,
)

__all__ = ["calculate_slide_margins", "calculate_inner_padding", "is_contained"]
