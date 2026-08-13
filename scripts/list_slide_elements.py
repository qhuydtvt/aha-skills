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


def parse_adsl_to_elements(
    dsl_text_or_path: str | Path,
    target_element_id: str | None = None,
) -> list[dict[str, Any]]:
    """Parse directive blocks (:::text, :::image, :::shape, :::icon, etc.) from offline .adsl text or files.

    Args:
        dsl_text_or_path: Raw DSL text string OR Path/str pointing to an .adsl file.
        target_element_id: Optional element ID to filter results.

    Returns:
        list[dict[str, Any]]: List of extracted slide element dicts.
    """
    dsl_text = ""
    if isinstance(dsl_text_or_path, Path):
        dsl_text = dsl_text_or_path.read_text(encoding="utf-8")
    elif isinstance(dsl_text_or_path, str):
        path_obj = Path(dsl_text_or_path)
        if dsl_text_or_path.endswith(".adsl") or (len(dsl_text_or_path) < 512 and path_obj.is_file()):
            dsl_text = path_obj.read_text(encoding="utf-8")
        else:
            dsl_text = dsl_text_or_path
    else:
        dsl_text = str(dsl_text_or_path)

    elements: list[dict[str, Any]] = []
    pattern = re.compile(
        r"(:::(?:[a-zA-Z0-9_-]+)([^\n]*)\n([\s\S]*?)(?:(?<=\n):::|(?<=^):::|\Z))",
        re.MULTILINE,
    )
    attr_kv_pattern = re.compile(r'([\w-]+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')

    for match in pattern.finditer(dsl_text):
        raw_dsl = match.group(1).strip()
        header_line = match.group(0).splitlines()[0] if match.group(0) else ""
        elem_type_match = re.match(r":::([a-zA-Z0-9_-]+)", header_line)
        elem_type = elem_type_match.group(1) if elem_type_match else "text"

        header_attr_str = match.group(2)
        body_text = match.group(3).strip()
        if body_text.endswith(":::"):
            body_text = body_text[:-3].strip()

        attributes: dict[str, str] = {}
        for attr_match in attr_kv_pattern.finditer(header_attr_str):
            k = attr_match.group(1)
            v = attr_match.group(2) or attr_match.group(3) or attr_match.group(4) or ""
            attributes[k] = v

        elem_id = attributes.get("id")
        if target_element_id and str(elem_id) != str(target_element_id):
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
                "type": elem_type,
            }
        )

    return elements


def list_slide_elements(
    slide_id: Any,
    target_element_id: str | None = None,
    client: AhaApiClient | None = None,
) -> list[dict[str, Any]]:
    """Query slide attributes API or read .adsl file offline and parse all element blocks.

    Args:
        slide_id: ID of the slide to inspect, OR Path/filename to an .adsl file.
        target_element_id: Optional element ID to filter results.
        client: Optional AhaApiClient instance.

    Returns:
        List[Dict[str, Any]]: List of extracted slide element dicts.
    """
    # Check if slide_id is a file path / .adsl file
    is_file = False
    if isinstance(slide_id, Path):
        is_file = True
    elif isinstance(slide_id, str):
        if slide_id.endswith(".adsl") or Path(slide_id).is_file():
            is_file = True

    if is_file:
        return parse_adsl_to_elements(slide_id, target_element_id=target_element_id)

    if client is None:
        client = AhaApiClient()

    try:
        res = client.get(SLIDE_ATTRIBUTES_PATH, params={"slideIds": str(slide_id)})
    except Exception as e:
        raise RuntimeError(f"Failed to fetch slide attributes for slide ID '{slide_id}': {e}") from e

    dsl_text = ""
    if isinstance(res, list):
        for item in res:
            if (str(item.get("slideId")) == str(slide_id) or len(res) == 1) and item.get("type") == "dsl":
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

    return parse_adsl_to_elements(dsl_text, target_element_id=target_element_id)


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
        elements = list_slide_elements(args.slide_id, target_element_id=args.element_id)
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
