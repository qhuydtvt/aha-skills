#!/usr/bin/env python3
"""Script to delete slide(s) from an AhaSlides presentation using AhaApiClient."""

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

DELETE_SLIDE_PATH = "/api/slide/"
DELETE_SLIDE_SOURCE = "editor.slide-delete"


def _parse_id(val: str | int) -> int | str:
    """Convert numeric string ID to integer, otherwise return as-is."""
    val_str = str(val).strip()
    if val_str.isdigit() or (val_str.startswith("-") and val_str[1:].isdigit()):
        return int(val_str)
    return val


def delete_slide(
    presentation_id: str | int,
    slide_ids: str | int | list[str | int],
) -> dict[str, Any]:
    """Delete slide(s) from a presentation on AhaSlides.

    Args:
        presentation_id: ID of the target presentation.
        slide_ids: A single slide ID or list of slide IDs to delete.

    Returns:
        Dict[str, Any]: API response from PATCH request.
    """
    client = AhaApiClient()

    pid = _parse_id(presentation_id)

    if not isinstance(slide_ids, list):
        if isinstance(slide_ids, (tuple, set)):
            sids_raw = list(slide_ids)
        else:
            sids_raw = [slide_ids]
    else:
        sids_raw = slide_ids

    parsed_slide_ids = [_parse_id(sid) for sid in sids_raw]

    payload: dict[str, Any] = {
        "presentationId": pid,
        "slides": [{"id": sid, "deleted": True} for sid in parsed_slide_ids],
    }

    return client.patch(
        DELETE_SLIDE_PATH,
        json_data=payload,
        params={"source": DELETE_SLIDE_SOURCE},
    )


def main():
    parser = argparse.ArgumentParser(
        description="Delete slide(s) from an AhaSlides presentation."
    )
    parser.add_argument(
        "presentation_id",
        help="ID of the target presentation",
    )
    parser.add_argument(
        "slide_id",
        nargs="+",
        help="Slide ID or list of slide IDs to delete",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw API response in JSON format",
    )

    args = parser.parse_args()

    try:
        result = delete_slide(args.presentation_id, args.slide_id)
    except Exception as e:  # noqa: BLE001
        print(f"Error deleting slide(s): {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    parsed_pid = _parse_id(args.presentation_id)
    parsed_sids = [_parse_id(sid) for sid in args.slide_id]
    sids_str = ", ".join(str(sid) for sid in parsed_sids)

    print("=== Slide(s) Deleted Successfully ===")
    print(f"Presentation ID:    {parsed_pid}")
    print(f"Deleted Slide ID(s): {sids_str}")
    if result:
        print(f"Response: {result}")


if __name__ == "__main__":
    main()
