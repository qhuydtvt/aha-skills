#!/usr/bin/env python3
"""Script to list user presentations on AhaSlides using the shared API client."""

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

LIST_PRESENTATIONS_PATH = "/api/presentation/list/infinity-scroll/v2"


def list_presentations(
    page: int = 1,
    sort_order: str = "desc",
    sort_column: str = "lastEditedAt",
    include_shared: bool = True,
    folder_id: str = "",
) -> Any:
    """Fetch user presentations from AhaSlides API."""
    client = AhaApiClient()
    params = {
        "page": page,
        "sortOrder": sort_order,
        "sortColumn": sort_column,
        "includeShared": "true" if include_shared else "false",
        "folderId": folder_id,
    }
    return client.get(LIST_PRESENTATIONS_PATH, params=params)


def extract_presentations(data: Any) -> list[dict[str, Any]]:
    """Extract list of presentation dicts from raw API response."""
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        for key in ["result", "presentations", "items", "data", "results", "list", "rows"]:
            val = data.get(key)
            if isinstance(val, list):
                return val
    return []


def print_presentations_table(items: list[dict[str, Any]], limit: int | None = None) -> None:
    """Print a clean summary table of presentations."""
    if limit is not None and limit > 0:
        items = items[:limit]

    if not items:
        print("No presentations found.")
        return

    print(f"Found {len(items)} presentation(s):\n")

    header = f"{'ID':<10} | {'TITLE/NAME':<35} | {'CODE':<10} | {'LAST EDITED':<24} | {'URL'}"
    separator = "-" * 115
    print(header)
    print(separator)

    for item in items:
        pres_id = str(item.get("id") or item.get("_id") or item.get("presentationId") or "N/A")
        title = str(item.get("name") or item.get("title") or "Untitled")
        if len(title) > 33:
            title = title[:30] + "..."
        access_code = str(item.get("accessCode") or item.get("code") or item.get("access_code") or "N/A")
        last_edited = str(item.get("lastEditedAt") or item.get("updatedAt") or item.get("createdAt") or "N/A")

        url = f"https://presenter.ahaslides.com/presentation/{pres_id}" if pres_id != "N/A" else "N/A"

        print(f"{pres_id:<10} | {title:<35} | {access_code:<10} | {last_edited:<24} | {url}")


def main():
    parser = argparse.ArgumentParser(description="List user presentations on AhaSlides.")
    parser.add_argument(
        "-p",
        "--page",
        type=int,
        default=1,
        help="Page number (default: 1)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=None,
        help="Limit number of items displayed",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    data = list_presentations(page=args.page)

    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        items = extract_presentations(data)
        if items:
            print_presentations_table(items, limit=args.limit)
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
