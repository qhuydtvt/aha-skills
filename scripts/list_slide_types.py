#!/usr/bin/env python3
"""Script to list available slide types from AhaSlides Marketplace API using AhaApiClient."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

SLIDE_TYPES_URL = "https://slides-marketplace.ahaslides.io/api/slide-types"


def get_slide_types(client: Optional[AhaApiClient] = None) -> List[Dict[str, Any]]:
    """Fetch slide types from the AhaSlides Marketplace API."""
    if client is None:
        client = AhaApiClient()

    response = client.get(SLIDE_TYPES_URL)

    if isinstance(response, dict):
        return response.get("slideTypes", [])
    elif isinstance(response, list):
        return response
    return []


def filter_slide_types(
    slide_types: List[Dict[str, Any]],
    category: Optional[str] = None,
    query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Filter slide types by category and search query."""
    filtered = []
    cat_lower = category.strip().lower() if category else None
    query_lower = query.strip().lower() if query else None

    for item in slide_types:
        config = item.get("ahaConfig", {}) if isinstance(item.get("ahaConfig"), dict) else {}

        item_name = str(item.get("name") or config.get("name") or "")
        item_type = str(config.get("type") or item.get("type") or "")
        item_cat = str(config.get("category") or item.get("category") or "")
        item_desc = str(item.get("desc") or config.get("desc") or "")
        pin_key = str(item.get("pinKey") or "")

        tags = item.get("tags") or config.get("tags") or []
        tags_str = " ".join(tags) if isinstance(tags, list) else str(tags)

        if cat_lower and cat_lower not in item_cat.lower():
            continue

        if query_lower:
            searchable_text = f"{item_name} {item_type} {item_cat} {item_desc} {pin_key} {tags_str}".lower()
            if query_lower not in searchable_text:
                continue

        filtered.append(item)

    return filtered


def format_summary_table(slide_types: List[Dict[str, Any]]) -> str:
    """Format slide types into a clean summary table."""
    if not slide_types:
        return "No slide types found matching the criteria."

    rows = []
    for item in slide_types:
        config = item.get("ahaConfig", {}) if isinstance(item.get("ahaConfig"), dict) else {}
        st_type = str(config.get("type") or item.get("type") or "N/A")
        name = str(item.get("name") or config.get("name") or "N/A")
        category = str(config.get("category") or item.get("category") or "N/A")
        desc = str(item.get("desc") or config.get("desc") or "").replace("\n", " ")
        if len(desc) > 55:
            desc = desc[:52] + "..."
        pin_key = str(item.get("pinKey") or "N/A")

        rows.append({
            "type": st_type,
            "name": name,
            "category": category,
            "desc": desc,
            "pin_key": pin_key,
        })

    type_len = max(max(len(r["type"]) for r in rows), 10)
    name_len = max(max(len(r["name"]) for r in rows), 15)
    cat_len = max(max(len(r["category"]) for r in rows), 10)
    desc_len = max(max(len(r["desc"]) for r in rows), 25)

    header = (
        f"{'TYPE':<{type_len}} | {'NAME':<{name_len}} | {'CATEGORY':<{cat_len}} | "
        f"{'DESCRIPTION':<{desc_len}}"
    )
    separator = "-" * len(header)

    lines = [header, separator]
    for r in rows:
        line = (
            f"{r['type']:<{type_len}} | {r['name']:<{name_len}} | {r['category']:<{cat_len}} | "
            f"{r['desc']:<{desc_len}}"
        )
        lines.append(line)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="List and filter available slide types from AhaSlides Marketplace API."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Optional search query to filter slide types (name, type, description, or tags).",
    )
    parser.add_argument(
        "--category",
        "-c",
        default=None,
        help="Filter slide types by category (e.g., content, quiz, poll, vote, game, media).",
    )
    parser.add_argument(
        "--query",
        "-q",
        dest="flag_query",
        default=None,
        help="Search query filter (overrides positional query if set).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output filtered slide types in JSON format.",
    )

    args = parser.parse_args()

    search_query = args.flag_query if args.flag_query is not None else args.query
    category_filter = args.category

    try:
        raw_slide_types = get_slide_types()
    except Exception as e:
        print(f"Error fetching slide types: {e}", file=sys.stderr)
        sys.exit(1)

    filtered_slide_types = filter_slide_types(
        raw_slide_types,
        category=category_filter,
        query=search_query,
    )

    if args.json:
        print(json.dumps(filtered_slide_types, indent=2))
        return

    total_count = len(raw_slide_types)
    match_count = len(filtered_slide_types)

    print("=== AhaSlides Available Slide Types ===")
    filters_applied = []
    if category_filter:
        filters_applied.append(f"category='{category_filter}'")
    if search_query:
        filters_applied.append(f"query='{search_query}'")

    filter_str = f" [Filters: {', '.join(filters_applied)}]" if filters_applied else ""
    print(f"Total Available: {total_count} | Matching: {match_count}{filter_str}\n")

    print(format_summary_table(filtered_slide_types))


if __name__ == "__main__":
    main()
