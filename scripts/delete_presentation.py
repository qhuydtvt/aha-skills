from __future__ import annotations
#!/usr/bin/env python3
"""Script to delete presentation(s) on AhaSlides using the shared API client."""

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

DELETE_PATH = "/api/presentation/"


def parse_presentation_id(item: str | int) -> int | str:
    """Convert presentation ID to integer if numeric, otherwise keep as string."""
    item_str = str(item).strip()
    if item_str.isdigit() or (item_str.startswith("-") and item_str[1:].isdigit()):
        return int(item_str)
    return item_str


def delete_presentation(presentation_ids: list[str | int]) -> dict:
    """Delete presentation(s) on AhaSlides given their ID(s)."""
    client = AhaApiClient()
    parsed_ids = [parse_presentation_id(pid) for pid in presentation_ids]
    payload = {
        "presentationIds": parsed_ids
    }
    return client.delete(DELETE_PATH, json_data=payload)


def main():
    parser = argparse.ArgumentParser(description="Delete presentation(s) on AhaSlides.")
    parser.add_argument(
        "presentation_id",
        nargs="+",
        help="Presentation ID or list of IDs to delete",
    )
    args = parser.parse_args()

    result = delete_presentation(args.presentation_id)

    parsed_ids = [parse_presentation_id(pid) for pid in args.presentation_id]
    id_str = ", ".join(str(pid) for pid in parsed_ids)
    print("=== Presentation(s) Deleted Successfully ===")
    print(f"Deleted Presentation ID(s): {id_str}")
    if result:
        print(f"Response: {result}")


if __name__ == "__main__":
    main()
