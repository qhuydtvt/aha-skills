from __future__ import annotations
#!/usr/bin/env python3
"""Script to read slide details and modifiable slide-level attributes on AhaSlides."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.list_slide_elements import list_slide_elements
from scripts.shared.api import AhaApiClient

DETAIL_PATH_TEMPLATE = "/api/presentation/detail/{presentation_id}"
LIST_PRESENTATIONS_PATH = "/api/presentation/list/infinity-scroll/v2"


def _parse_id(val: str | int) -> int | str:
    """Convert numeric string ID to integer, otherwise return as-is."""
    val_str = str(val).strip()
    if val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
        return int(val_str)
    return val


def _resolve_presentation_id(
    slide_id: str | int, client: AhaApiClient
) -> tuple[int | str, dict[str, Any]]:
    """Search user presentations to find the presentation_id containing the given slide_id.

    Returns:
        tuple[int | str, dict[str, Any]]: Presentation ID and slide dict.
    """
    sid_str = str(slide_id).strip()
    page = 1
    max_pages = 10

    while page <= max_pages:
        try:
            res = client.get(LIST_PRESENTATIONS_PATH, params={"page": page})
        except Exception as e:
            raise RuntimeError(f"Failed to fetch presentations list: {e}") from e

        items = []
        if isinstance(res, list):
            items = res
        elif isinstance(res, dict):
            for k in ["result", "presentations", "items", "data", "results", "list"]:
                if isinstance(res.get(k), list):
                    items = res[k]
                    break

        if not items:
            break

        for item in items:
            pid = item.get("id") or item.get("_id") or item.get("presentationId")
            if not pid:
                continue

            try:
                detail = client.get(DETAIL_PATH_TEMPLATE.format(presentation_id=pid))
            except Exception:  # noqa: BLE001, S112
                continue

            slides = detail.get("Slides") or detail.get("slides") or []
            for s in slides:
                if str(s.get("id") or s.get("_id")) == sid_str:
                    return pid, s

        page += 1

    raise ValueError(f"Could not resolve presentation ID for slide ID '{slide_id}'.")


def read_slide(
    slide_id: str | int,
    presentation_id: str | int | None = None,
    client: AhaApiClient | None = None,
) -> dict[str, Any]:
    """Read slide details and slide-level properties from AhaSlides.

    Args:
        slide_id: ID of the slide to read.
        presentation_id: Optional ID of the parent presentation.
        client: Optional AhaApiClient instance.

    Returns:
        dict[str, Any]: Slide metadata, properties, and modifiable attributes.
    """
    if client is None:
        client = AhaApiClient()

    parsed_slide_id = _parse_id(slide_id)
    sid_str = str(parsed_slide_id)

    target_slide: dict[str, Any] | None = None
    resolved_pid: int | str | None = None

    if presentation_id is not None:
        resolved_pid = _parse_id(presentation_id)
        try:
            detail = client.get(DETAIL_PATH_TEMPLATE.format(presentation_id=resolved_pid))
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch detail for presentation ID '{resolved_pid}': {e}"
            ) from e

        slides = detail.get("Slides") or detail.get("slides") or []
        for s in slides:
            if str(s.get("id") or s.get("_id")) == sid_str:
                target_slide = s
                break

        if target_slide is None:
            raise ValueError(
                f"Slide ID '{slide_id}' not found in presentation ID '{resolved_pid}'."
            )
    else:
        resolved_pid, target_slide = _resolve_presentation_id(parsed_slide_id, client)

    slide_type = target_slide.get("type") or target_slide.get("slideType") or "unknown"
    order = target_slide.get("order")
    base_colour = target_slide.get("baseColour", "")
    text_colour = target_slide.get("textColour", "")
    background_image = target_slide.get("backgroundImage")
    visibility = target_slide.get("visibility")

    # Determine elements_count
    elements_count = 0
    try:
        elements = list_slide_elements(parsed_slide_id, client=client)
        elements_count = len(elements)
    except Exception:  # noqa: BLE001
        opts = target_slide.get("SlideOptions") or target_slide.get("options") or []
        if isinstance(opts, list) and opts:
            elements_count = len(opts)

    return {
        "id": parsed_slide_id,
        "presentation_id": resolved_pid,
        "type": slide_type,
        "order": order,
        "baseColour": base_colour,
        "textColour": text_colour,
        "backgroundImage": background_image,
        "visibility": visibility,
        "elements_count": elements_count,
        "modifiable_attributes": [
            "baseColour",
            "textColour",
            "backgroundImage",
            "visibility",
        ],
        "raw_slide": target_slide,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Read slide properties and modifiable slide-level attributes."
    )
    parser.add_argument(
        "slide_id",
        nargs="?",
        help="ID of the target slide (required).",
    )
    parser.add_argument(
        "-p",
        "--presentation-id",
        dest="presentation_id",
        default=None,
        help="Optional presentation ID.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON format.",
    )

    args = parser.parse_args()

    if not args.slide_id:
        print("Error: 'slide_id' argument is required.", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    try:
        result = read_slide(
            slide_id=args.slide_id,
            presentation_id=args.presentation_id,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error reading slide: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"=== Slide Details (ID: {result['id']}) ===")
    print(f"Presentation ID: {result['presentation_id']}")
    print(f"Type:            {result['type']}")
    print(f"Order:           {result['order']}")
    print(f"Base Colour:     {result['baseColour']}")
    print(f"Text Colour:     {result['textColour']}")
    print(f"Background Img:  {result['backgroundImage'] or 'None'}")
    print(f"Visibility:      {result['visibility']}")
    print(f"Elements Count:  {result['elements_count']}")
    print(f"Modifiable Attrs: {', '.join(result['modifiable_attributes'])}")


if __name__ == "__main__":
    main()
