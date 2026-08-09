#!/usr/bin/env python3
"""Script to create a new slide in an AhaSlides presentation using AhaApiClient."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

CREATE_SLIDE_PATH = "/api/slide/create/"


def create_slide(
    presentation_id: Any,
    slide_type: str = "content-v2",
    order: int | None = None,
    at_end: bool = False,
) -> dict[str, Any]:
    """Create a new slide in the specified presentation.

    Args:
        presentation_id: ID of the target presentation.
        slide_type: Type of slide to create (default: 'content-v2').
        order: Optional integer order position for the slide.
        at_end: If True (or order == -1), append slide at the end of the presentation.

    Returns:
        dict[str, Any]: API response object containing created slide details.
    """
    client = AhaApiClient()

    # Normalize presentation_id to int if numeric
    try:
        pid = int(presentation_id)
    except (ValueError, TypeError):
        pid = presentation_id

    # 1. Fetch presentation detail to get current slide order before creation
    slides_before: list[dict[str, Any]] = []
    try:
        from scripts.read_presentation import fetch_presentation_detail
        pres_detail = fetch_presentation_detail(client, str(pid))
        slides_before = pres_detail.get("Slides") or pres_detail.get("slides") or []
    except Exception:  # noqa: BLE001
        slides_before = []

    target_order = order
    if at_end or order == -1 or target_order is None:
        target_order = len(slides_before) + 1

    payload: dict[str, Any] = {
        "presentationId": pid,
        "type": slide_type,
        "order": target_order,
    }

    res = client.post(CREATE_SLIDE_PATH, json_data=payload)

    # 2. Update slide sorting order via PUT /api/slide/sort-slide/{presentation_id}
    new_slide_id = res.get("id") or res.get("_id") if isinstance(res, dict) else None
    if new_slide_id:
        try:
            existing_ids = [s.get("id") for s in slides_before if s.get("id") and s.get("id") != new_slide_id]
            idx = target_order - 1 if target_order and target_order <= len(existing_ids) else len(existing_ids)
            existing_ids.insert(idx, new_slide_id)

            sort_payload = [{"order": i + 1, "id": sid} for i, sid in enumerate(existing_ids)]
            client.put(f"/api/slide/sort-slide/{pid}", json_data={"sort": sort_payload})
        except Exception:  # noqa: BLE001, S110
            pass

    return res


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
        help="Optional slide position/order (integer, or -1 for end).",
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
        "--at-end",
        "--end",
        "-e",
        action="store_true",
        help="Append new slide at the end of the presentation.",
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
        result = create_slide(args.presentation_id, slide_type=slide_type, order=order, at_end=args.at_end)
    except Exception as e:  # noqa: BLE001
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
