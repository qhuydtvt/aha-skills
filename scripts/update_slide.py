from __future__ import annotations
#!/usr/bin/env python3
"""Script to update slide-level properties on AhaSlides."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.read_slide import _resolve_presentation_id
from scripts.shared.api import AhaApiClient

UPDATE_SLIDE_PATH = "/api/slide/"
UPDATE_SLIDE_SOURCE = "editor.slide-edit"


def _parse_id(val: str | int) -> int | str:
    """Convert numeric string ID to integer, otherwise return as-is."""
    val_str = str(val).strip()
    if val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
        return int(val_str)
    return val


def update_slide(
    slide_id: str | int,
    presentation_id: str | int | None = None,
    base_colour: str | None = None,
    text_colour: str | None = None,
    background_image: str | None = None,
    visibility: int | str | None = None,
    apply_to_all: bool = False,
    client: AhaApiClient | None = None,
) -> dict[str, Any]:
    """Update slide-level properties on AhaSlides.

    Args:
        slide_id: ID of the slide to update.
        presentation_id: Optional ID of the parent presentation.
        base_colour: Optional base/background color hex or string.
        text_colour: Optional text color hex or string.
        background_image: Optional background image URL.
        visibility: Optional slide visibility value.
        apply_to_all: If True, apply properties to all slides in presentation.
        client: Optional AhaApiClient instance.

    Returns:
        dict[str, Any]: Updated slide properties and API response.
    """
    if client is None:
        client = AhaApiClient()

    parsed_slide_id = _parse_id(slide_id)

    if presentation_id is not None:
        parsed_pid = _parse_id(presentation_id)
    else:
        parsed_pid, _ = _resolve_presentation_id(parsed_slide_id, client)

    slide_update: dict[str, Any] = {
        "id": parsed_slide_id,
        "presentationId": parsed_pid,
    }

    if base_colour is not None:
        slide_update["baseColour"] = base_colour
    if text_colour is not None:
        slide_update["textColour"] = text_colour
    if background_image is not None:
        slide_update["backgroundImage"] = background_image
    if visibility is not None:
        try:
            slide_update["visibility"] = int(visibility)
        except (ValueError, TypeError):
            slide_update["visibility"] = visibility

    if len(slide_update) == 2:
        raise ValueError("At least one property must be specified for update.")

    payload: dict[str, Any] = {
        "presentationId": parsed_pid,
        "slides": [slide_update],
    }

    if apply_to_all:
        payload["action"] = "apply-to-other-slides"

    api_res = client.patch(
        UPDATE_SLIDE_PATH,
        json_data=payload,
        params={"source": UPDATE_SLIDE_SOURCE},
    )

    return {
        "slide_id": parsed_slide_id,
        "presentation_id": parsed_pid,
        "updated_properties": slide_update,
        "apply_to_all": apply_to_all,
        "api_response": api_res,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Update slide-level properties on AhaSlides."
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
        "--base-color",
        "--bg-color",
        dest="base_colour",
        default=None,
        help="Base/background color (e.g. '#1e293b').",
    )
    parser.add_argument(
        "--text-color",
        dest="text_colour",
        default=None,
        help="Text color (e.g. '#ffffff').",
    )
    parser.add_argument(
        "--background-image",
        dest="background_image",
        default=None,
        help="Background image URL.",
    )
    parser.add_argument(
        "--visibility",
        dest="visibility",
        default=None,
        help="Slide visibility value (integer).",
    )
    parser.add_argument(
        "--apply-to-all",
        dest="apply_to_all",
        action="store_true",
        help="Apply these properties to all other slides in the presentation.",
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
        result = update_slide(
            slide_id=args.slide_id,
            presentation_id=args.presentation_id,
            base_colour=args.base_colour,
            text_colour=args.text_colour,
            background_image=args.background_image,
            visibility=args.visibility,
            apply_to_all=args.apply_to_all,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error updating slide: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("=== Slide Updated Successfully ===")
    print(f"Slide ID:        {result['slide_id']}")
    print(f"Presentation ID: {result['presentation_id']}")
    print(f"Apply to All:    {result['apply_to_all']}")
    print("Updated Properties:")
    for k, v in result["updated_properties"].items():
        if k != "id":
            print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
