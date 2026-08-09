#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.list_slide_elements import list_slide_elements
from scripts.shared.api import AhaApiClient

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

def lint_slide(slide_id: str, client: AhaApiClient | None = None) -> tuple[dict[str, tuple[float, float, float, float]], list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    elements = list_slide_elements(slide_id, client=client)
    boxes = {}
    syntax_errors = []
    overflows = []
    
    # Raw DSL Lint: Check raw DSL text for malformed directives like :::::: or missing newline block breaks
    if client is None:
        client = AhaApiClient()

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
            
    overlaps = []
    eids = list(boxes.keys())
    for i in range(len(eids)):
        for j in range(i + 1, len(eids)):
            id1, id2 = eids[i], eids[j]
            if check_overlap(boxes[id1], boxes[id2]):
                overlaps.append((id1, id2))
                
    return boxes, overlaps, syntax_errors, overflows

def main():
    parser = argparse.ArgumentParser(description="Lint a slide for overlapping elements, leaks, and overflows.")
    parser.add_argument("slide_id", help="ID of the target slide.")
    args = parser.parse_args()
    
    client = AhaApiClient()
    boxes, overlaps, syntax_errors, overflows = lint_slide(args.slide_id, client=client)
    
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
        
    if failed:
        sys.exit(1)
    else:
        print("\nSUCCESS: No overlaps, overflows, or syntax leaks detected.")
        sys.exit(0)

if __name__ == "__main__":
    main()
