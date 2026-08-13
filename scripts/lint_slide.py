#!/usr/bin/env python3
"""Lint a slide or offline .adsl file for overlaps, syntax leaks, canvas overflows, color contrast, and content density."""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.list_slide_elements import list_slide_elements, parse_adsl_to_elements
from scripts.read_slide import read_slide
from scripts.shared.api import AhaApiClient
from scripts.shared.lib.contrast import evaluate_contrast

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


def parse_dimension(val: Any, max_val: int) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if s.endswith("%"):
        return max_val * float(s[:-1]) / 100.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def get_bounding_box(elem: dict[str, Any]) -> tuple[float, float, float, float]:
    """Returns (left, top, right, bottom)"""
    attrs = elem.get("attributes", {})
    width_val = attrs.get("w") or attrs.get("width") or elem.get("width") or ("80%" if elem.get("preset") in ["title", "body", "bullet", "subtitle", "heading"] else ("60%" if elem.get("preset") == "video" else ("50%" if elem.get("preset") == "image" else (360 if elem.get("preset") == "timer" else "50%"))))
    height_val = attrs.get("h") or attrs.get("height") or elem.get("height")

    width = parse_dimension(width_val, CANVAS_WIDTH)
    if height_val is None:
        if elem.get("preset") == "timer":
            height = 360
        elif elem.get("preset") in ["image", "video"]:
            height = width * 9 / 16
        else:
            text = elem.get("text", "")
            preset_type = elem.get("preset", "body")
            font_size = 60 if preset_type in ["title", "heading"] else (40 if preset_type == "subtitle" else 30)
            fs_attr = attrs.get("fontSize") or attrs.get("font-size") or elem.get("fontSize") or elem.get("font-size")
            if fs_attr:
                try:
                    font_size = float(re.sub(r"[^\d\.]", "", str(fs_attr)))
                except ValueError:
                    pass
            chars_per_line = max(1, int(width / (font_size * 0.6)))
            lines = sum(max(1, (len(line) + chars_per_line - 1) // chars_per_line) for line in text.split("\n"))
            height = max(font_size * 1.5, lines * font_size * 1.5)
    else:
        height = parse_dimension(height_val, CANVAS_HEIGHT)

    raw_x = attrs.get("x") if attrs.get("x") is not None else (attrs.get("offsetX") or attrs.get("offset_x") or elem.get("offset_x") or 0)
    raw_y = attrs.get("y") if attrs.get("y") is not None else (attrs.get("offsetY") or attrs.get("offset_y") or elem.get("offset_y") or 0)
    offset_x = parse_dimension(raw_x, CANVAS_WIDTH)
    offset_y = parse_dimension(raw_y, CANVAS_HEIGHT)

    at = attrs.get("at") or elem.get("at") or ("top-left" if "x" in attrs or "y" in attrs else "center")
    if at == "center":
        left = CANVAS_WIDTH / 2 + offset_x - width / 2
        top = CANVAS_HEIGHT / 2 + offset_y - height / 2
    else:
        left, top = offset_x, offset_y

    return (left, top, left + width, top + height)


def check_overlap(box1: tuple[float, float, float, float], box2: tuple[float, float, float, float]) -> bool:
    l1, t1, r1, b1 = box1
    l2, t2, r2, b2 = box2
    return not (r1 <= l2 or l1 >= r2 or b1 <= t2 or t1 >= b2)


def is_contained(inner: tuple[float, float, float, float], outer: tuple[float, float, float, float]) -> bool:
    """Check if inner box is contained within outer box."""
    l1, t1, r1, b1 = inner
    l2, t2, r2, b2 = outer
    if l2 <= (l1 + r1) / 2.0 <= r2 and t2 <= (t1 + b1) / 2.0 <= b2:
        return True
    inter_l, inter_r = max(l1, l2), min(r1, r2)
    inter_t, inter_b = max(t1, t2), min(b1, b2)
    if inter_r > inter_l and inter_b > inter_t:
        return ((inter_r - inter_l) * (inter_b - inter_t)) / max(1.0, (r1 - l1) * (b1 - t1)) >= 0.5
    return False


def count_bullet_items(text: str) -> int:
    """Count bullet points or numbered list items in text."""
    if not text:
        return 0
    p = re.compile(r"^\s*(?:[•\-*+→]|\d+[\.\)]|[a-zA-Z][\.\)])\s*\S+")
    return sum(1 for line in text.splitlines() if p.match(line))


def lint_slide(
    target: str | Path,
    client: AhaApiClient | None = None,
    contrast_level: str = "AA",
    live: bool = False,
) -> tuple[
    dict[str, tuple[float, float, float, float]],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[tuple[str, str]],
]:
    """Lint a slide or offline .adsl file.

    Args:
        target: Live slide ID (numeric string) or Path / filename to an .adsl file.
        client: Optional AhaApiClient instance (used for live slide queries).
        contrast_level: WCAG level ("AA" or "AAA").
        live: Force live slide linting API call if True.

    Returns:
        tuple containing:
            - boxes: Map of element ID to bounding box tuple (l, t, r, b).
            - overlaps: List of (elem_id_1, elem_id_2) overlaps.
            - syntax_errors: List of (elem_id, message) syntax leaks.
            - overflows: List of (elem_id, message) canvas overflows.
            - contrast_errors: List of (elem_id, message) contrast failures.
            - density_errors: List of (elem_id, message) content length/density violations.
            - symmetry_errors: List of (elem_id, message) right margin and inner padding symmetry violations.
    """
    boxes = {}
    syntax_errors: list[tuple[str, str]] = []
    overflows: list[tuple[str, str]] = []
    contrast_errors: list[tuple[str, str]] = []
    density_errors: list[tuple[str, str]] = []
    symmetry_errors: list[tuple[str, str]] = []

    # 1. Determine if offline file or live slide
    is_file = False
    file_path = None
    target_str = str(target).strip()

    if isinstance(target, Path):
        is_file = True
        file_path = target
    elif not live:
        p = Path(target_str)
        if target_str.endswith(".adsl") or p.is_file():
            is_file = True
            file_path = p

    slide_base_color = "#ffffff"
    slide_text_color = "#000000"
    dsl_text = ""

    if is_file and file_path is not None:
        dsl_text = file_path.read_text(encoding="utf-8")
        elements = parse_adsl_to_elements(dsl_text)

        # Try extracting base and text colors from header comments or attributes
        base_match = re.search(r"#\s*@baseColour:\s*(\S+)", dsl_text)
        if base_match:
            slide_base_color = base_match.group(1)
        text_match = re.search(r"#\s*@textColour:\s*(\S+)", dsl_text)
        if text_match:
            slide_text_color = text_match.group(1)
    else:
        slide_id = target_str
        if client is None:
            client = AhaApiClient()
        elements = list_slide_elements(slide_id, client=client)

        try:
            slide_info = read_slide(slide_id, client=client)
            if slide_info.get("baseColour"):
                slide_base_color = slide_info["baseColour"]
            if slide_info.get("textColour"):
                slide_text_color = slide_info["textColour"]
        except Exception:  # noqa: BLE001, S110
            pass

        try:
            res_attr = client.get("/api/v2/slides/attributes", params={"slideIds": str(slide_id)})
            if isinstance(res_attr, list) and res_attr:
                attrs_dict = res_attr[0].get("attributes", {})
                if isinstance(attrs_dict, str):
                    dsl_text = attrs_dict
                elif isinstance(attrs_dict, dict):
                    dsl_text = attrs_dict.get("dsl", "")
                    if attrs_dict.get("baseColour"):
                        slide_base_color = attrs_dict["baseColour"]
                    if attrs_dict.get("textColour"):
                        slide_text_color = attrs_dict["textColour"]
        except Exception:  # noqa: BLE001, S110
            pass

    # Only override slide_base_color to dark slate if explicitly specified in DSL metadata/styling
    if "background: dark" in dsl_text.lower() or "background: #0f172a" in dsl_text.lower():
        slide_base_color = "#0F172A"
    elif not slide_base_color:
        slide_base_color = "#FFFFFF"

    # Raw DSL Lint: Check raw DSL text for malformed directives like :::::: or missing newline block breaks
    if dsl_text and ("::::::" in dsl_text or "::::" in dsl_text):
        syntax_errors.append(
            (
                "slide_dsl",
                "Malformed directive boundary detected in raw DSL (e.g. '::::::text' without proper newline separation).",
            )
        )

    # Total slide counters for content density check
    total_slide_chars = 0
    total_slide_bullets = 0

    for elem in elements:
        eid = str(elem.get("id") or "unknown")
        boxes[eid] = get_bounding_box(elem)

        # Content Lint: Check for leaked DSL or HTML syntax
        text = elem.get("text", "")
        if (
            ":::text" in text
            or "::::::" in text
            or "preset=" in text
            or "offsetY=" in text
            or "<br>" in text.lower()
        ):
            syntax_errors.append((eid, "Leaked DSL or HTML syntax detected in element text."))

        # Overflow Lint: Check if element bleeds off the canvas (1280x720)
        l, t, r, b = boxes[eid]
        if t < 0 or b > CANVAS_HEIGHT or l < 0 or r > CANVAS_WIDTH:
            overflows.append(
                (
                    eid,
                    f"Element bounding box ({l:.1f}, {t:.1f}, {r:.1f}, {b:.1f}) overflows canvas (1280x720).",
                )
            )

        # Content Length & Density Validation (Single Element Level)
        text_lines = text.splitlines() if text else []
        elem_line_count = len(text_lines)
        elem_char_count = len(text)
        elem_bullet_count = count_bullet_items(text)

        total_slide_chars += elem_char_count
        total_slide_bullets += elem_bullet_count

        if elem_line_count > 8:
            density_errors.append((eid, f"Single element lines ({elem_line_count}) exceeds 8 max limit."))
        if elem_char_count > 350:
            density_errors.append((eid, f"Single element length ({elem_char_count} chars) exceeds 350 max limit."))

    # Content Length & Density Validation (Slide Level)
    if total_slide_chars > 750:
        density_errors.append(("slide_content", f"Total slide chars ({total_slide_chars}) exceeds 750 max. Recommend splitting into 2 slides."))
    if total_slide_bullets > 8:
        density_errors.append(("slide_content", f"Total slide items ({total_slide_bullets}) exceeds 8 max. Recommend splitting into 2 slides."))

    # Identify potential container elements (shapes/boxes with background/bg/fill)
    containers = []
    for elem in elements:
        attrs = elem.get("attributes", {})
        bg_val = attrs.get("background") or attrs.get("bg") or attrs.get("fill")
        if bg_val:
            containers.append((elem, bg_val))

    # Header / Divider Column Alignment & Grid Symmetry Linting
    header_elements = []
    for elem in elements:
        eid_str = str(elem.get("id") or "unknown")
        eid_lower = eid_str.lower()
        preset = elem.get("preset")
        if preset in ["title", "heading", "subtitle"] or "divider" in eid_lower or "title" in eid_lower:
            header_elements.append(elem)

    if header_elements:
        min_header_left = min(boxes[str(e.get("id") or "unknown")][0] for e in header_elements)
        max_header_right = max(boxes[str(e.get("id") or "unknown")][2] for e in header_elements)

        for c_elem, _ in containers:
            c_id = str(c_elem.get("id") or "unknown")
            c_box = boxes[c_id]
            c_left, c_top, c_right, c_bottom = c_box

            # Check if this container is top-level (not nested inside another parent container)
            is_nested = False
            for parent_elem, _ in containers:
                p_id = str(parent_elem.get("id") or "unknown")
                if p_id == c_id:
                    continue
                if is_contained(c_box, boxes[p_id]):
                    is_nested = True
                    break

            if not is_nested:
                if abs(c_left - min_header_left) <= 30 and c_right > max_header_right + 50:
                    c_width = c_right - c_left
                    diff = c_right - max_header_right
                    msg = (
                        f"Container '{c_id}' (right edge x={c_right:.1f}, width={c_width:.1f}) "
                        f"extends {diff:.1f}px beyond header/divider column boundary (x={max_header_right:.1f}). "
                        f"Align container width to header column bounds."
                    )
                    symmetry_errors.append((c_id, msg))

    # Inner Padding & Collective Slide-Level Padding Symmetry Linting
    for elem in elements:
        eid = str(elem.get("id") or "unknown")
        elem_box = boxes[eid]
        left, top, right, bottom = elem_box

        # 1. Spatial search for parent container shape enclosure
        parent_container = None
        best_container_area = float("inf")
        for cont_elem, _ in containers:
            cont_id = str(cont_elem.get("id") or "unknown")
            if cont_id == eid:
                continue
            cont_box = boxes[cont_id]
            if is_contained(elem_box, cont_box):
                cont_area = (cont_box[2] - cont_box[0]) * (cont_box[3] - cont_box[1])
                if cont_area < best_container_area:
                    best_container_area = cont_area
                    parent_container = cont_elem

        # 2. Evaluate inner padding symmetry rule for nested elements inside container shapes
        if parent_container is not None:
            parent_id = str(parent_container.get("id") or "unknown")
            parent_left, _, parent_right, _ = boxes[parent_id]
            inner_left_padding = left - parent_left
            inner_right_padding = parent_right - right
            if inner_right_padding < inner_left_padding - 1.0:
                max_boundary = parent_right - inner_left_padding
                msg = (
                    f"Inner right padding ({inner_right_padding:.1f}px) inside container '{parent_id}' "
                    f"is less than inner left padding ({inner_left_padding:.1f}px). Right edge x={right:.1f} exceeds max boundary {max_boundary:.1f}."
                )
                symmetry_errors.append((eid, msg))

    # Collective Slide-Level Padding Lint Validation
    non_full_bleed_boxes = [box for box in boxes.values() if (box[2] - box[0]) < CANVAS_WIDTH]
    if non_full_bleed_boxes:
        slide_left = min(box[0] for box in non_full_bleed_boxes)
        slide_right = max(box[2] for box in non_full_bleed_boxes)
        slide_left_padding = slide_left
        slide_right_padding = CANVAS_WIDTH - slide_right
        if slide_right_padding < slide_left_padding - 1.0:
            msg = (
                f"Slide content right padding ({slide_right_padding:.1f}px) is less than left padding ({slide_left_padding:.1f}px). "
                f"Max content right edge x={slide_right:.1f}px exceeds max symmetric boundary ({CANVAS_WIDTH - slide_left_padding:.1f}px). "
                f"Recommended: padding right = padding left for symmetrical look."
            )
            symmetry_errors.append(("slide_padding", msg))

    # Contrast Lint (Spatial Container Overlap Aware)
    for elem in elements:
        eid = str(elem.get("id") or "unknown")
        attrs = elem.get("attributes", {})
        text = elem.get("text", "").strip()

        # Skip contrast check for non-text or empty text elements
        elem_type = elem.get("type", "text")
        preset = elem.get("preset", "body")
        if (
            elem_type in ["image", "video", "timer", "shape", "pattern", "icon"]
            or preset in ["shape", "rect", "line"]
            or elem.get("kind") is not None
            or "shape" in str(eid)
        ) and (not text or text == ":::" or text.startswith(":::")):
            continue

        # 1. Resolve Foreground Text Color
        fg_color = attrs.get("color") or attrs.get("textColour") or attrs.get("text-color")
        if text and not fg_color:
            color_match = re.search(
                r'(?:color|style=["\'][^"\']*color):\s*([^"\';\s>]+)', text, re.IGNORECASE
            )
            if color_match:
                fg_color = color_match.group(1)
        if not fg_color:
            fg_color = slide_text_color

        # 2. Resolve Background Container Color
        bg_color = attrs.get("background") or attrs.get("bg") or attrs.get("fill")
        if not bg_color:
            # Spatial search for container enclosure
            elem_box = boxes[eid]
            best_container_area = float("inf")
            for cont_elem, cont_bg in containers:
                cont_id = str(cont_elem.get("id") or "unknown")
                if cont_id == eid:
                    continue
                cont_box = boxes[cont_id]
                if is_contained(elem_box, cont_box):
                    cont_area = (cont_box[2] - cont_box[0]) * (cont_box[3] - cont_box[1])
                    if cont_area < best_container_area:
                        best_container_area = cont_area
                        bg_color = cont_bg

        if not bg_color:
            bg_color = slide_base_color or "#FFFFFF"

        # 3. Determine text size (Large vs Normal)
        preset = elem.get("preset", "body")
        font_size = 30
        if preset in ["title", "heading"]:
            font_size = 60
        elif preset == "subtitle":
            font_size = 40

        fs_attr = attrs.get("fontSize") or attrs.get("font-size")
        if fs_attr:
            try:
                font_size = float(re.sub(r"[^\d\.]", "", str(fs_attr)))
            except ValueError:
                pass

        is_large_text = font_size >= 24.0

        # Resolve theme color keywords (text, muted, surface, bg) to actual hex values
        is_dark_canvas = (
            slide_base_color.lower() in ["#0f172a", "#000000", "#1e293b", "bg"]
            or (slide_base_color.startswith("#") and len(slide_base_color) >= 7 and int(slide_base_color[1:3], 16) < 128)
        )
        theme_map = {
            "text": "#F8FAFC" if is_dark_canvas else "#0F172A",
            "muted": "#94A3B8" if is_dark_canvas else "#64748B",
            "surface": "#1E293B" if is_dark_canvas else "#F8FAFC",
            "bg": slide_base_color,
            "transparent": slide_base_color,
        }
        resolved_fg = theme_map.get(str(fg_color).lower(), fg_color)
        resolved_bg = theme_map.get(str(bg_color).lower(), bg_color)

        eval_res = evaluate_contrast(
            fg_val=resolved_fg,
            bg_val=resolved_bg,
            canvas_bg_val=slide_base_color,
            is_large_text=is_large_text,
            level=contrast_level,
        )

        if not eval_res["pass"]:
            msg = (
                f"Low contrast ratio {eval_res['ratio']}:1 (fg: '{fg_color}', bg: '{bg_color}'). "
                f"Minimum required for WCAG {eval_res['level']} {'large' if is_large_text else 'normal'} text is {eval_res['required']}:1."
            )
            contrast_errors.append((eid, msg))

    overlaps: list[tuple[str, str]] = []
    eids = list(boxes.keys())
    elem_by_id = {str(e.get("id") or "unknown"): e for e in elements}

    for i in range(len(eids)):
        for j in range(i + 1, len(eids)):
            id1, id2 = eids[i], eids[j]
            box1, box2 = boxes[id1], boxes[id2]
            if check_overlap(box1, box2):
                e1 = elem_by_id.get(id1, {})
                e2 = elem_by_id.get(id2, {})
                type1, type2 = e1.get("type"), e2.get("type")
                kind1 = e1.get("attributes", {}).get("kind") or ("shape" if type1 == "shape" else None)
                kind2 = e2.get("attributes", {}).get("kind") or ("shape" if type2 == "shape" else None)

                # Skip overlap error if one element is a background container shape enclosing the other
                if (type1 in ["shape", "pattern"] or kind1) and is_contained(box2, box1):
                    continue
                if (type2 in ["shape", "pattern"] or kind2) and is_contained(box1, box2):
                    continue

                overlaps.append((id1, id2))

    return boxes, overlaps, syntax_errors, overflows, contrast_errors, density_errors, symmetry_errors


def main():
    parser = argparse.ArgumentParser(description="Lint slide or offline .adsl file for overlaps, leaks, overflows, contrast, density, and symmetry.")
    parser.add_argument("target", nargs="?", default=None, help="Path to offline .adsl file OR ID of live slide.")
    parser.add_argument("-f", "--file", dest="file_path", default=None, help="Path to offline .adsl file.")
    parser.add_argument("--live", action="store_true", help="Force live slide verification via AhaSlides API.")
    parser.add_argument("--contrast-level", choices=["AA", "AAA"], default="AA", help="WCAG contrast compliance level.")
    parser.add_argument("--strict-contrast", action="store_true", help="Fail on contrast errors.")
    args = parser.parse_args()

    target_input = args.file_path or args.target
    if not target_input:
        parser.error("Either a target argument (.adsl file / slide_id) or --file must be specified.")

    is_live = args.live
    client = AhaApiClient() if is_live or not (str(target_input).endswith(".adsl") or Path(target_input).is_file()) else None

    try:
        boxes, overlaps, syntax_errors, overflows, contrast_errors, density_errors, symmetry_errors = lint_slide(
            target_input, client=client, contrast_level=args.contrast_level, live=is_live
        )
    except Exception as e:
        print(f"Error running slide linter on target '{target_input}': {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Linting target: {target_input} ({'Live Slide' if is_live else 'Offline .adsl'}) | {len(boxes)} elements.")
    for eid, box in boxes.items():
        print(f"  {eid}: {box}")

    failed = False
    if syntax_errors:
        print("\nERROR: Syntax leaks detected!")
        for eid, err in syntax_errors:
            print(f"  Element {eid}: {err}")
        failed = True

    if overflows:
        print("\nERROR: Canvas overflow detected!")
        for eid, err in overflows:
            print(f"  Element {eid}: {err}")
        failed = True

    if overlaps:
        print("\nERROR: Overlaps detected!")
        for id1, id2 in overlaps:
            print(f"  Element {id1} overlaps with {id2}")
        failed = True

    if density_errors:
        print("\nERROR: Content length & density limit exceeded!")
        for eid, err in density_errors:
            print(f"  Element/Scope {eid}: {err}")
        failed = True

    if contrast_errors:
        print("\nERROR: Low color contrast detected!")
        for eid, err in contrast_errors:
            print(f"  Element {eid}: {err}")
        failed = True

    if symmetry_errors:
        print("\nERROR: Symmetry violations detected!")
        for eid, err in symmetry_errors:
            print(f"  Element {eid}: {err}")
        failed = True

    if failed:
        sys.exit(1)
    print("\nSUCCESS: All layout, density, syntax, contrast, symmetry, and boundary checks passed.")


if __name__ == "__main__":
    main()
