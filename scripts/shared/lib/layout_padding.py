#!/usr/bin/env python3
"""Shared Layout & Slide Padding Calculation Engine.

# Coordinate System & AhaSlides Canvas Reality
# =============================================
# AhaSlides DSL uses a 1280x720 coordinate space. However, the presenter UI
# renders a visual overlay on the RIGHT side (logo, participant counter, timer)
# that visually occupies approximately the last 80-100px of the canvas width.
# This means content placed near x=1200 in DSL coords will appear visually
# very close to the screen edge or overlap with AhaSlides UI chrome.
#
# Empirical analysis of 60+ professionally designed AhaSlides templates shows:
#   - Most full-content layouts have max_right <= 800px (right padding >= 480px)
#   - Wide/full-width layouts have max_right <= 1040px (right padding >= 240px)
#   - Only a small number of banner/hero layouts exceed max_right=1120px
#
# Based on this, the safe right margin threshold for multi-column card layouts
# is significantly higher than the left margin. The collective slide-level
# padding check should enforce:
#   - Minimum LEFT padding:  >= 40px  (canvas left is safe)
#   - Minimum RIGHT padding: >= 80px  (canvas right has AhaSlides UI chrome)
#   - Symmetry tolerance: <= 15px difference between left and right padding
#     (allows intentional asymmetric layouts but flags extreme imbalances)
"""

from __future__ import annotations
from typing import Any, Sequence

CANVAS_WIDTH = 1280.0
CANVAS_HEIGHT = 720.0

# Minimum safe DSL pixel margin from canvas LEFT boundary.
# Canvas left edge is safe — no AhaSlides presenter chrome overlay.
DEFAULT_MIN_SAFE_LEFT_MARGIN = 40.0

# Minimum safe DSL pixel margin from canvas RIGHT boundary.
# AhaSlides presenter UI overlays (logo top-right, participant counter
# bottom-right) visually occupy the rightmost portion of the canvas.
#
# CALIBRATION (measured 2026-08-13 from live slide screenshot):
#   Mapping: screen_x = 0.7417 * dsl_x + 62.0
#   - DSL x=0    -> screen x=62px   (canvas has 62px left offset)
#   - DSL x=1200 -> screen x=952px  (only 35px from 987px screen width)
#   - AhaSlides logo LEFT edge at screen ~870px = DSL x~1089
#   - DSL x=1160 -> screen 922px = 52px PAST the logo (content hidden)
#   - DSL x=1040 -> screen 833px = 37px BEFORE the logo (safe)
#
# Therefore safe right content boundary = DSL x <= 1040
# => min_safe_right_margin = 1280 - 1040 = 240px
DEFAULT_MIN_SAFE_RIGHT_MARGIN = 240.0

# Maximum allowed absolute difference between left and right slide padding.
# Within this tolerance, layouts are considered visually balanced.
DEFAULT_SYMMETRY_TOLERANCE = 15.0

# Backward-compatible alias
DEFAULT_MIN_SAFE_MARGIN = DEFAULT_MIN_SAFE_LEFT_MARGIN


def is_contained(
    inner_box: tuple[float, float, float, float],
    outer_box: tuple[float, float, float, float],
) -> bool:
    """Check if inner bounding box (l, t, r, b) is spatially contained within outer bounding box."""
    l1, t1, r1, b1 = inner_box
    l2, t2, r2, b2 = outer_box

    # Check center containment
    center_x = (l1 + r1) / 2.0
    center_y = (t1 + b1) / 2.0
    if l2 <= center_x <= r2 and t2 <= center_y <= b2:
        return True

    # Check 50% overlap containment
    inter_l, inter_r = max(l1, l2), min(r1, r2)
    inter_t, inter_b = max(t1, t2), min(b1, b2)
    if inter_r > inter_l and inter_b > inter_t:
        intersection_area = (inter_r - inter_l) * (inter_b - inter_t)
        inner_area = max(1.0, (r1 - l1) * (b1 - t1))
        return (intersection_area / inner_area) >= 0.5

    return False


def calculate_inner_padding(
    elem_box: tuple[float, float, float, float],
    parent_box: tuple[float, float, float, float],
) -> dict[str, float | bool]:
    """Calculate inner padding of an element inside its parent container box."""
    l_elem, t_elem, r_elem, b_elem = elem_box
    l_parent, t_parent, r_parent, b_parent = parent_box

    inner_left = l_elem - l_parent
    inner_top = t_elem - t_parent
    inner_right = r_parent - r_elem
    inner_bottom = b_parent - b_elem

    return {
        "inner_left_padding": inner_left,
        "inner_top_padding": inner_top,
        "inner_right_padding": inner_right,
        "inner_bottom_padding": inner_bottom,
        "is_right_deficient": inner_right < (inner_left - 1.0),
    }


def calculate_slide_margins(
    boxes: dict[str, tuple[float, float, float, float]],
    elements: Sequence[dict[str, Any]] | None = None,
    canvas_width: float = CANVAS_WIDTH,
    min_safe_margin: float = DEFAULT_MIN_SAFE_LEFT_MARGIN,
    min_safe_left_margin: float = DEFAULT_MIN_SAFE_LEFT_MARGIN,
    min_safe_right_margin: float = DEFAULT_MIN_SAFE_RIGHT_MARGIN,
    symmetry_tolerance: float = DEFAULT_SYMMETRY_TOLERANCE,
) -> dict[str, Any]:
    """Pure mathematical calculation of collective slide-level padding across top-level structural elements.

    Args:
        boxes: Map of element ID -> bounding box (left, top, right, bottom).
        elements: Optional raw element list used to identify background shapes & containers.
        canvas_width: Width of the slide canvas (default 1280.0).
        min_safe_margin: Deprecated alias for min_safe_left_margin.
        min_safe_left_margin: Minimum safe LEFT edge margin in px (default 40px).
        min_safe_right_margin: Minimum safe RIGHT edge margin in px (default 80px).
            AhaSlides presenter UI chrome (logo, participant counter) visually
            occupies the rightmost ~80px, so right_padding < 80px causes content
            to appear visually cramped or overlapped by presenter UI elements.
        symmetry_tolerance: Maximum allowed difference between left and right padding (default 15px).

    Returns:
        Dictionary containing slide_left_padding, slide_right_padding, min_left_id, max_right_id,
        is_symmetric, meets_minimum, meets_left_minimum, meets_right_minimum, and diagnostic metrics.
    """
    if not boxes:
        return {
            "slide_left_padding": canvas_width / 2.0,
            "slide_right_padding": canvas_width / 2.0,
            "min_left_id": None,
            "max_right_id": None,
            "structural_element_ids": [],
            "diff_padding": 0.0,
            "is_symmetric": True,
            "meets_minimum": True,
        }

    # 1. Identify container shapes (elements with background/bg/fill attributes)
    container_ids: set[str] = set()
    if elements:
        for elem in elements:
            eid = str(elem.get("id") or "unknown")
            attrs = elem.get("attributes", {})
            if attrs.get("background") or attrs.get("bg") or attrs.get("fill"):
                container_ids.add(eid)

    # 2. Filter top-level structural elements (excluding full-bleed backdrops & nested children)
    struct_boxes: dict[str, tuple[float, float, float, float]] = {}

    for eid, box in boxes.items():
        width = box[2] - box[0]

        # Rule A: Skip full-bleed / near full-bleed backdrop shapes (>= 95% of canvas width)
        if width >= (0.95 * canvas_width):
            continue

        # Rule B: Skip child elements nested inside container shapes
        is_nested = False
        if container_ids:
            for parent_id in container_ids:
                if parent_id == eid or parent_id not in boxes:
                    continue
                if is_contained(box, boxes[parent_id]):
                    is_nested = True
                    break

        if not is_nested:
            struct_boxes[eid] = box

    # Fallback to all non-full-bleed boxes if structural filtering yields empty set
    if not struct_boxes:
        struct_boxes = {
            eid: box for eid, box in boxes.items() if (box[2] - box[0]) < (0.95 * canvas_width)
        }

    if not struct_boxes:
        struct_boxes = dict(boxes)

    # 3. Calculate collective left and right slide boundaries
    min_left = min(box[0] for box in struct_boxes.values())
    max_right = max(box[2] for box in struct_boxes.values())

    min_left_id = next(eid for eid, box in struct_boxes.items() if box[0] == min_left)
    max_right_id = next(eid for eid, box in struct_boxes.items() if box[2] == max_right)

    slide_left_padding = min_left
    slide_right_padding = canvas_width - max_right
    diff_padding = abs(slide_left_padding - slide_right_padding)

    is_symmetric = diff_padding <= symmetry_tolerance
    meets_left_minimum = slide_left_padding >= min_safe_left_margin
    meets_right_minimum = slide_right_padding >= min_safe_right_margin
    meets_minimum = meets_left_minimum and meets_right_minimum

    return {
        "slide_left_padding": slide_left_padding,
        "slide_right_padding": slide_right_padding,
        "min_left_id": min_left_id,
        "max_right_id": max_right_id,
        "structural_element_ids": list(struct_boxes.keys()),
        "diff_padding": diff_padding,
        "is_symmetric": is_symmetric,
        "meets_minimum": meets_minimum,
        "meets_left_minimum": meets_left_minimum,
        "meets_right_minimum": meets_right_minimum,
        "min_safe_left_margin": min_safe_left_margin,
        "min_safe_right_margin": min_safe_right_margin,
        "min_safe_margin": min_safe_left_margin,  # backward compat
        "symmetry_tolerance": symmetry_tolerance,
    }
