#!/usr/bin/env python3
"""Script to list elements (:::text, :::image, :::video, :::timer, etc.) from a slide's DSL content."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

SLIDE_ATTRIBUTES_PATH = "/api/v2/slides/attributes"


def _parse_num(val: Any) -> Any:
    """Parse numeric string to int or float if possible, else return original value."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def list_slide_elements(
    slide_id: Any,
    element_id: str | None = None,
    client: AhaApiClient | None = None,
) -> list[dict[str, Any]]:
    """Query slide attributes API and parse all element blocks (text, image, video, timer, etc.) from DSL.

    Args:
        slide_id: ID of the slide to inspect.
        element_id: Optional element ID to filter results.
        client: Optional AhaApiClient instance.

    Returns:
        List[Dict[str, Any]]: List of extracted slide element dicts.
    """
    if client is None:
        client = AhaApiClient()

    try:
        res = client.get(SLIDE_ATTRIBUTES_PATH, params={"slideIds": str(slide_id)})
    except Exception as e:
        raise RuntimeError(f"Failed to fetch slide attributes for slide ID '{slide_id}': {e}") from e

    dsl_text = ""
    if isinstance(res, list):
        for item in res:
            if str(item.get("slideId")) == str(slide_id) or len(res) == 1:
                attrs = item.get("attributes")
                if isinstance(attrs, str):
                    dsl_text = attrs
                    break
                elif isinstance(attrs, dict) and "dsl" in attrs:
                    dsl_text = str(attrs["dsl"])
                    break
    elif isinstance(res, dict):
        attrs = res.get("attributes")
        if isinstance(attrs, str):
            dsl_text = attrs
        elif isinstance(attrs, dict):
            dsl_text = str(attrs.get("dsl", ""))

    if not dsl_text or not isinstance(dsl_text, str):
        return []

    elements: list[dict[str, Any]] = []
    pattern = re.compile(r"(:::(?:text|shape|image|icon|video|timer)([^\n]*)\n(.*?)(?:\n:::\s*|\Z))", re.DOTALL)
    attr_kv_pattern = re.compile(r'([\w-]+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')

    for match in pattern.finditer(dsl_text):
        raw_dsl = match.group(1).strip()
        header_attr_str = match.group(2)
        body_text = match.group(3).strip()

        attributes: dict[str, str] = {}
        for attr_match in attr_kv_pattern.finditer(header_attr_str):
            k = attr_match.group(1)
            v = attr_match.group(2) or attr_match.group(3) or attr_match.group(4) or ""
            attributes[k] = v

        elem_id = attributes.get("id")
        if element_id and str(elem_id) != str(element_id):
            continue

        preset = attributes.get("preset")
        at = attributes.get("at")
        width = attributes.get("width")

        raw_off_x = (
            attributes.get("offsetX")
            or attributes.get("offset_x")
            or attributes.get("offset-x")
        )
        raw_off_y = (
            attributes.get("offsetY")
            or attributes.get("offset_y")
            or attributes.get("offset-y")
        )

        offset_x = _parse_num(raw_off_x)
        offset_y = _parse_num(raw_off_y)

        elements.append(
            {
                "id": elem_id,
                "preset": preset,
                "at": at,
                "width": width,
                "offset_x": offset_x,
                "offset_y": offset_y,
                "attributes": attributes,
                "text": body_text,
                "raw_dsl": raw_dsl,
                "type": match.group(1).split()[0].replace(":::", ""),
            }
        )

    return elements


def main():
    parser = argparse.ArgumentParser(
        description="List elements (:::text, :::image, :::video, :::timer, etc.) from a slide's DSL content."
    )
    parser.add_argument(
        "slide_id",
        nargs="?",
        help="ID of the target slide (required).",
    )
    parser.add_argument(
        "-e",
        "--element-id",
        dest="element_id",
        default=None,
        help="Specific element ID to inspect/explore.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format.",
    )

    args = parser.parse_args()

    if not args.slide_id:
        print("Error: 'slide_id' argument is required.", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    try:
        elements = list_slide_elements(args.slide_id, element_id=args.element_id)
    except Exception as e:  # noqa: BLE001
        print(f"Error listing slide elements: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(elements, indent=2))
        return

    print(f"=== Slide Elements for Slide '{args.slide_id}' (Total: {len(elements)}) ===")
    if not elements:
        print("No elements found on this slide.")
        return

    for idx, elem in enumerate(elements, 1):
        print(f"\n[{idx}] Element ID: {elem.get('id') or 'N/A'} (Type: {elem.get('type') or 'N/A'})")
        if elem.get('preset'):
            print(f"    Preset:     {elem.get('preset')}")
        pos_parts = []
        if elem.get("at"):
            pos_parts.append(f"at={elem['at']}")
        if elem.get("width"):
            pos_parts.append(f"width={elem['width']}")
        if elem.get("offset_x") is not None or elem.get("offset_y") is not None:
            pos_parts.append(f"offset=({elem.get('offset_x')}, {elem.get('offset_y')})")
        if pos_parts:
            print(f"    Position:   {', '.join(pos_parts)}")

        other_attrs = {
            k: v
            for k, v in elem.get("attributes", {}).items()
            if k not in ("id", "preset", "at", "width", "offset-x", "offset-y", "offset_x", "offset_y", "offsetX", "offsetY")
        }
        if other_attrs:
            attr_str = ", ".join(f"{k}={v}" for k, v in other_attrs.items())
            print(f"    Attributes: {attr_str}")

        text_snip = elem.get("text", "")
        if "\n" in text_snip:
            first_line = text_snip.splitlines()[0]
            print(f"    Text:       \"{first_line}\" (+ {len(text_snip.splitlines()) - 1} more lines)")
        else:
            print(f"    Text:       \"{text_snip}\"")


if __name__ == "__main__":
    main()
