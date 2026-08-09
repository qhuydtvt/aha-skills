#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.list_slide_elements import list_slide_elements
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
    width_val = attrs.get("width", elem.get("width"))
    height_val = attrs.get("height", elem.get("height"))
    
    # Defaults based on preset
    preset = elem.get("preset")
    if width_val is None:
        if preset in ["title", "body", "bullet", "subtitle", "heading"]:
            width_val = "80%"
        elif preset == "image":
            width_val = "50%"
        elif preset == "video":
            width_val = "60%"
        elif preset == "timer":
            width_val = 360
        else:
            width_val = "50%"
            
    width = parse_dimension(width_val, CANVAS_WIDTH)
    
    if height_val is None:
        if preset == "timer":
            height = 360
        elif preset == "image" or preset == "video":
            height = width * 9 / 16 # Assume 16:9
        else:
            # Estimate text height
            text = elem.get("text", "")
            preset_type = elem.get("preset", "body")
            
            font_size = 30
            if preset_type in ["title", "heading"]:
                font_size = 60
            elif preset_type == "subtitle":
                font_size = 40
                
            char_width = font_size * 0.6
            chars_per_line = max(1, int(width / char_width))
            
            lines = 0
            for line in text.split("\n"):
                lines += max(1, (len(line) + chars_per_line - 1) // chars_per_line)
                
            height = max(font_size * 1.5, lines * font_size * 1.5)
    else:
        height = parse_dimension(height_val, CANVAS_HEIGHT)
        
    offset_x = parse_dimension(elem.get("offset_x") or attrs.get("offsetX") or 0, CANVAS_WIDTH)
    offset_y = parse_dimension(elem.get("offset_y") or attrs.get("offsetY") or 0, CANVAS_HEIGHT)
    
    at = elem.get("at") or attrs.get("at") or "center"
    
    if at == "center":
        cx = CANVAS_WIDTH / 2 + offset_x
        cy = CANVAS_HEIGHT / 2 + offset_y
        left = cx - width / 2
        top = cy - height / 2
    else:
        # Assuming top-left for other cases if not center
        left = offset_x
        top = offset_y
        
    return (left, top, left + width, top + height)

def check_overlap(box1: tuple[float, float, float, float], box2: tuple[float, float, float, float]) -> bool:
    l1, t1, r1, b1 = box1
    l2, t2, r2, b2 = box2
    return not (r1 <= l2 or l1 >= r2 or b1 <= t2 or t1 >= b2)

def is_contained(inner: tuple[float, float, float, float], outer: tuple[float, float, float, float]) -> bool:
    """Check if inner box is contained within or substantially overlaps outer box."""
    l1, t1, r1, b1 = inner
    l2, t2, r2, b2 = outer
    cx, cy = (l1 + r1) / 2.0, (t1 + b1) / 2.0
    if l2 <= cx <= r2 and t2 <= cy <= b2:
        return True
    
    inter_l = max(l1, l2)
    inter_r = min(r1, r2)
    inter_t = max(t1, t2)
    inter_b = min(b1, b2)
    if inter_r > inter_l and inter_b > inter_t:
        inter_area = (inter_r - inter_l) * (inter_b - inter_t)
        inner_area = max(1.0, (r1 - l1) * (b1 - t1))
        if inter_area / inner_area >= 0.5:
            return True
    return False

def lint_slide(
    slide_id: str,
    client: AhaApiClient | None = None,
    contrast_level: str = "AA",
) -> tuple[
    dict[str, tuple[float, float, float, float]],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[tuple[str, str]],
    list[tuple[str, str]],
]:
    elements = list_slide_elements(slide_id, client=client)
    boxes = {}
    syntax_errors = []
    overflows = []
    contrast_errors = []
    
    if client is None:
        client = AhaApiClient()

    # Retrieve slide base and text colors
    slide_base_color = "#ffffff"
    slide_text_color = "#000000"
    try:
        slide_info = read_slide(slide_id, client=client)
        if slide_info.get("baseColour"):
            slide_base_color = slide_info["baseColour"]
        if slide_info.get("textColour"):
            slide_text_color = slide_info["textColour"]
    except Exception:  # noqa: BLE001, S110
        pass

    # Raw DSL Lint: Check raw DSL text for malformed directives like :::::: or missing newline block breaks
    try:
        res = client.get("/api/v2/slides/attributes", params={"slideIds": str(slide_id)})
        dsl_text = ""
        if isinstance(res, list) and res:
            attrs = res[0].get("attributes", {})
            dsl_text = attrs if isinstance(attrs, str) else attrs.get("dsl", "")
        elif isinstance(res, dict):
            attrs = res.get("attributes", {})
            dsl_text = attrs if isinstance(attrs, str) else attrs.get("dsl", "")

        if "::::::" in dsl_text or "::::" in dsl_text:
            syntax_errors.append(("slide_dsl", "Malformed directive boundary detected in raw DSL (e.g. '::::::text' without proper newline separation)."))
    except Exception:  # noqa: BLE001, S110
        pass

    for elem in elements:
        eid = elem.get("id")
        boxes[eid] = get_bounding_box(elem)
        
        # Content Lint: Check for leaked DSL or HTML syntax
        text = elem.get("text", "")
        if ":::text" in text or "::::::" in text or "preset=" in text or "offsetY=" in text or "<br>" in text.lower():
            syntax_errors.append((eid, "Leaked DSL or HTML syntax detected in element text."))
            
        # Overflow Lint: Check if element bleeds off the canvas (1280x720)
        l, t, r, b = boxes[eid]
        if t < 0 or b > CANVAS_HEIGHT or l < 0 or r > CANVAS_WIDTH:
            overflows.append((eid, f"Element bounding box ({l:.1f}, {t:.1f}, {r:.1f}, {b:.1f}) overflows canvas (1280x720)."))

    # Identify potential container elements (shapes/boxes with background/bg/fill)
    containers = []
    for elem in elements:
        attrs = elem.get("attributes", {})
        bg_val = attrs.get("background") or attrs.get("bg") or attrs.get("fill")
        if bg_val:
            containers.append((elem, bg_val))

    # Contrast Lint (Option 2: Spatial Container Overlap Aware)
    for elem in elements:
        eid = elem.get("id")
        attrs = elem.get("attributes", {})
        text = elem.get("text", "").strip()
        
        # Skip contrast check for non-text or empty text elements
        elem_type = elem.get("type", "text")
        if elem_type in ["image", "video", "timer"] and not text:
            continue

        # 1. Resolve Foreground Text Color
        fg_color = attrs.get("color") or attrs.get("textColour") or attrs.get("text-color")
        if not fg_color:
            import re
            color_match = re.search(r'(?:color|style=["\'][^"\']*color):\s*([^"\';\s>]+)', text, re.IGNORECASE)
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
                cont_id = cont_elem.get("id")
                if cont_id == eid:
                    continue
                cont_box = boxes[cont_id]
                if is_contained(elem_box, cont_box):
                    cont_area = (cont_box[2] - cont_box[0]) * (cont_box[3] - cont_box[1])
                    if cont_area < best_container_area:
                        best_container_area = cont_area
                        bg_color = cont_bg

        if not bg_color:
            bg_color = slide_base_color

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

        eval_res = evaluate_contrast(
            fg_val=fg_color,
            bg_val=bg_color,
            canvas_bg_val=slide_base_color,
            is_large_text=is_large_text,
            level=contrast_level,
        )

        if not eval_res["pass"]:
            text_kind = "large" if is_large_text else "normal"
            msg = (
                f"Low contrast ratio {eval_res['ratio']}:1 (fg: '{fg_color}', bg: '{bg_color}'). "
                f"Minimum required for WCAG {eval_res['level']} {text_kind} text is {eval_res['required']}:1."
            )
            contrast_errors.append((eid, msg))

    overlaps = []
    eids = list(boxes.keys())
    for i in range(len(eids)):
        for j in range(i + 1, len(eids)):
            id1, id2 = eids[i], eids[j]
            if check_overlap(boxes[id1], boxes[id2]):
                overlaps.append((id1, id2))
                
    return boxes, overlaps, syntax_errors, overflows, contrast_errors

def main():
    parser = argparse.ArgumentParser(description="Lint a slide for overlapping elements, leaks, overflows, and color contrast.")
    parser.add_argument("slide_id", help="ID of the target slide.")
    parser.add_argument("--contrast-level", choices=["AA", "AAA"], default="AA", help="WCAG contrast compliance level (default: AA).")
    parser.add_argument("--strict-contrast", action="store_true", help="Fail with non-zero exit code on contrast errors.")
    args = parser.parse_args()
    
    client = AhaApiClient()
    boxes, overlaps, syntax_errors, overflows, contrast_errors = lint_slide(args.slide_id, client=client, contrast_level=args.contrast_level)
    
    print(f"Linting slide: {args.slide_id}")
    print(f"Found {len(boxes)} elements.")
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

    if contrast_errors:
        print("\nWARNING/ERROR: Low color contrast detected!")
        for eid, err in contrast_errors:
            print(f"  Element {eid}: {err}")
        if args.strict_contrast:
            failed = True
        
    if failed:
        sys.exit(1)
    else:
        print("\nSUCCESS: No overlaps, overflows, syntax leaks, or severe errors detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()

