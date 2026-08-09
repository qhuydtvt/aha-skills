#!/usr/bin/env python3
"""Script to create a new slide in an AhaSlides presentation using AhaApiClient."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

CREATE_SLIDE_PATH = "/api/slide/create/"


def create_slide(
    presentation_id: Any,
    slide_type: str = "content-v2",
    order: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a new slide in the specified presentation.

    Args:
        presentation_id: ID of the target presentation.
        slide_type: Type of slide to create (default: 'content-v2').
        order: Optional integer order position for the slide.

    Returns:
        Dict[str, Any]: API response object containing created slide details.
    """
    client = AhaApiClient()

    # Normalize presentation_id to int if numeric
    try:
        pid = int(presentation_id)
    except (ValueError, TypeError):
        pid = presentation_id

    payload: Dict[str, Any] = {
        "presentationId": pid,
        "type": slide_type,
    }
    if order is not None:
        payload["order"] = order

    return client.post(CREATE_SLIDE_PATH, json_data=payload)


def main():
    parser = argparse.ArgumentParser(
        description="Create a new slide in an AhaSlides presentation."
    )
    parser.add_argument(
        "presentation_id",
        nargs="?",
        help="ID of the target presentation (required).",
    )
    parser.add_argument(
        "type",
        nargs="?",
        default="content-v2",
        help="Slide type (default: 'content-v2').",
    )
    parser.add_argument(
        "order",
        nargs="?",
        type=int,
        default=None,
        help="Optional slide position/order (integer).",
    )
    parser.add_argument(
        "--type",
        "-t",
        dest="flag_type",
        default=None,
        help="Slide type (overrides positional argument if set).",
    )
    parser.add_argument(
        "--order",
        "-o",
        dest="flag_order",
        type=int,
        default=None,
        help="Slide order (overrides positional argument if set).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw API response in JSON format.",
    )

    args = parser.parse_args()

    if not args.presentation_id:
        print("Error: 'presentation_id' argument is required.", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    slide_type = args.flag_type if args.flag_type is not None else args.type
    order = args.flag_order if args.flag_order is not None else args.order

    try:
        result = create_slide(args.presentation_id, slide_type=slide_type, order=order)
    except Exception as e:
        print(f"Error creating slide: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("=== Slide Created Successfully ===")
    if isinstance(result, dict):
        slide_id = (
            result.get("id")
            or result.get("_id")
            or result.get("slideId")
            or (result.get("slide", {}).get("id") if isinstance(result.get("slide"), dict) else None)
        )
        pres_id = result.get("presentationId") or args.presentation_id
        res_type = result.get("type") or slide_type
        res_order = result.get("order") if result.get("order") is not None else order

        if slide_id:
            print(f"Slide ID:        {slide_id}")
        print(f"Presentation ID: {pres_id}")
        print(f"Type:            {res_type}")
        if res_order is not None:
            print(f"Order:           {res_order}")
    else:
        print(result)


if __name__ == "__main__":
    main()
