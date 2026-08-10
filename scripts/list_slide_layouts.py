#!/usr/bin/env python3
"""Script to list and inspect slide layout templates and v2 DSL structures.

Supports:
1. Listing pre-built v2 DSL layout presets (e.g., intro_caption_hero, grid_3cards, split_matrix_2col, process_flow_3step).
2. Fetching the complete 167 layouts catalog from AhaSlides API (matching the 167 Layouts modal UI).
3. Extracting layout DSL templates directly from any live presentation ID.

Usage:
    python3 scripts/list_slide_layouts.py
    python3 scripts/list_slide_layouts.py --all-167
    python3 scripts/list_slide_layouts.py --category Content
    python3 scripts/list_slide_layouts.py -p <presentation_id>
    python3 scripts/list_slide_layouts.py --layout intro_caption_hero
    python3 scripts/list_slide_layouts.py --json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.read_presentation import fetch_presentation_detail
from scripts.shared.api import AhaApiClient

PUBLIC_TEMPLATES_PATH = "/api/slide/public-templates"
MARKETPLACE_SLIDE_TYPES_URL = "https://slides-marketplace.ahaslides.io/api/slide-types?env=production"

# Pre-built v2 DSL Layout Presets Library
BUILTIN_LAYOUT_PRESETS: dict[str, dict[str, Any]] = {
    "intro_caption_hero": {
        "name": "01 Intro Caption + Hero Title + Body + Accent Rect",
        "category": "Cover",
        "description": "Top-left aligned section caption, large 56px hero title, body narrative block, and bottom accent line shape.",
        "elements_count": 4,
        "dsl_template": """---
content-v2: 1280x720
version: 1
---

:::text id={id_caption} at=top-left width=600 height=32 offsetX=80 offsetY=72 preset=caption color=muted
{caption_text}
:::

:::text id={id_title} at=top-left width=1120 height=88 offsetX=80 offsetY=152 preset=title align=left color=text fontSize=56
{title_text}
:::

:::text id={id_body} at=top-left width=1000 height=160 offsetX=80 offsetY=296 preset=body align=left color=text
{body_text}
:::

:::shape id={id_shape} at=top-left width=64 height=8 offsetX=80 offsetY=560 kind=rect fill=text
:::
"""
    },
    "grid_3cards": {
        "name": "02 3-Column Feature Cards Grid (Pricing / 3 Tiers)",
        "category": "Content",
        "description": "Center title with 3 horizontally spaced feature cards (-360, 0, +360 offset_x).",
        "elements_count": 4,
        "dsl_template": """---
content-v2: 1280x720
version: 1
---

:::text id={id_title} at=center width=85% offsetX=0 offsetY=-240 preset=title color=#F8FAFC
{title_text}
:::

:::text id={id_card1} at=center width=26% offsetX=-360 offsetY=-50 preset=body color=#F8FAFC background=#1E293B border-radius=12 padding=14
### 1. {card1_title}
{card1_desc}
:::

:::text id={id_card2} at=center width=26% offsetX=0 offsetY=-50 preset=body color=#06B6D4 background=#1E293B border-radius=12 padding=14
### 2. {card2_title}
{card2_desc}
:::

:::text id={id_card3} at=center width=26% offsetX=360 offsetY=-50 preset=body color=#F8FAFC background=#1E293B border-radius=12 padding=14
### 3. {card3_title}
{card3_desc}
:::
"""
    },
    "split_matrix_2col": {
        "name": "03 Split 2-Column Matrix (Approach A vs B / Compare)",
        "category": "Compare",
        "description": "Left/right container cards (-280, +280 offset_x) with a full-width bottom framework banner.",
        "elements_count": 4,
        "dsl_template": """---
content-v2: 1280x720
version: 1
---

:::text id={id_title} at=center width=85% offsetX=0 offsetY=-240 preset=title color=#F8FAFC
{title_text}
:::

:::text id={id_left} at=center width=42% offsetX=-280 offsetY=-50 preset=body color=#F8FAFC background=#1E293B border-radius=12 padding=14
### 💬 {left_title}
{left_content}
:::

:::text id={id_right} at=center width=42% offsetX=280 offsetY=-50 preset=body color=#F8FAFC background=#1E293B border-radius=12 padding=14
### 🛑 {right_title}
{right_content}
:::

:::text id={id_banner} at=center width=85% offsetX=0 offsetY=160 preset=body color=#06B6D4 background=#1E293B border-radius=12 padding=14
### 📋 {banner_title}
{banner_content}
:::
"""
    },
    "process_flow_3step": {
        "name": "04 3-Step Horizontal Process Flow",
        "category": "Section",
        "description": "Top header, preferred channel banner, and 3 sequential step cards.",
        "elements_count": 5,
        "dsl_template": """---
content-v2: 1280x720
version: 1
---

:::text id={id_title} at=center width=85% offsetX=0 offsetY=-240 preset=title color=#F8FAFC
{title_text}
:::

:::text id={id_banner} at=center width=85% offsetX=0 offsetY=-140 preset=body color=#06B6D4 background=#1E293B border-radius=12 padding=10
🗣️ **Preferred Channel:** {preferred_channel}
:::

:::text id={id_step1} at=center width=26% offsetX=-360 offsetY=0 preset=body color=#F8FAFC background=#1E293B border-radius=12 padding=14
### Step 1: {step1_title}
{step1_detail}
:::

:::text id={id_step2} at=center width=26% offsetX=0 offsetY=0 preset=body color=#F8FAFC background=#1E293B border-radius=12 padding=14
### Step 2: {step2_title}
{step2_detail}
:::

:::text id={id_step3} at=center width=26% offsetX=360 offsetY=0 preset=body color=#06B6D4 background=#1E293B border-radius=12 padding=14
### Step 3: {step3_title}
{step3_detail}
:::
"""
    }
}


def fetch_all_167_layouts(client: AhaApiClient | None = None) -> list[dict[str, Any]]:
    """Fetch and aggregate the complete 167 layout items catalog matching the UI modal."""
    if client is None:
        client = AhaApiClient()

    all_layouts: list[dict[str, Any]] = []

    # 1. Fetch 128 Public v2 DSL Layout Templates
    try:
        pub_res = client.get(PUBLIC_TEMPLATES_PATH)
        if isinstance(pub_res, list):
            for idx, item in enumerate(pub_res):
                meta = item.get("metadata") or {}
                if not isinstance(meta, dict):
                    meta = {}
                title = item.get("title") or item.get("subheading") or f"Layout #{idx + 1}"
                cat = meta.get("category") or meta.get("layoutCategory") or "Content"
                all_layouts.append({
                    "id": item.get("id"),
                    "name": title,
                    "type": "freestyle-v2",
                    "category": cat,
                    "source": "public-templates",
                    "thumbnail": item.get("contentTemplateThumbnail") or (item.get("backgroundImage", {}).get("thumbnail") if isinstance(item.get("backgroundImage"), dict) else None),
                })
    except Exception as e:  # noqa: BLE001
        print(f"Warning: Failed to fetch public templates: {e}", file=sys.stderr)

    # 2. Fetch 39 Marketplace Interactive Slide Types
    try:
        mkt_res = client.get(MARKETPLACE_SLIDE_TYPES_URL)
        items = mkt_res.get("slideTypes", []) if isinstance(mkt_res, dict) else (mkt_res if isinstance(mkt_res, list) else [])
        for item in items:
            cat = item.get("category") or "Interactive"
            all_layouts.append({
                "id": item.get("pinKey") or item.get("type"),
                "name": item.get("name"),
                "type": item.get("type"),
                "category": cat,
                "source": "marketplace-slide-types",
                "icon": item.get("icon"),
            })
    except Exception as e:  # noqa: BLE001
        print(f"Warning: Failed to fetch marketplace slide types: {e}", file=sys.stderr)

    return all_layouts


def extract_layouts_from_presentation(presentation_id: str, client: AhaApiClient | None = None) -> list[dict[str, Any]]:
    """Fetch presentation slides and extract layout DSL structures."""
    if client is None:
        client = AhaApiClient()

    detail = fetch_presentation_detail(client, presentation_id)
    slides = detail.get("slides") or detail.get("Slides") or []
    extracted: list[dict[str, Any]] = []

    for idx, slide in enumerate(slides):
        sid = slide.get("id") or slide.get("_id")
        stype = slide.get("type") or slide.get("slideType")
        layout_prop = slide.get("layout", "")

        dsl_text = ""
        attrs = slide.get("attributes")
        if isinstance(attrs, dict) and "dsl" in attrs:
            dsl_text = str(attrs["dsl"])
        else:
            try:
                res = client.get("/api/v2/slides/attributes", params={"slideIds": str(sid)})
                if isinstance(res, list) and res and "attributes" in res[0]:
                    dsl_text = str(res[0]["attributes"].get("dsl", ""))
            except Exception:  # noqa: BLE001
                dsl_text = ""

        extracted.append({
            "slide_number": idx + 1,
            "slide_id": sid,
            "slide_type": stype,
            "layout_property": layout_prop,
            "base_color": slide.get("baseColour", ""),
            "text_color": slide.get("textColour", ""),
            "dsl_text": dsl_text,
            "has_dsl": bool(dsl_text.strip()),
        })

    return extracted


def main():
    parser = argparse.ArgumentParser(description="List and inspect slide layout templates and v2 DSL structures.")
    parser.add_argument(
        "--all",
        "-a",
        dest="fetch_all",
        action="store_true",
        help="Fetch and list all available slide layout templates from AhaSlides API.",
    )
    parser.add_argument(
        "--categories",
        "--list-categories",
        dest="list_categories",
        action="store_true",
        help="Dynamically extract and list all unique layout categories available from the API.",
    )
    parser.add_argument(
        "--category",
        "-c",
        dest="category",
        help="Filter layouts by category (e.g. Cover, Section, Content, Statistics, Visual, Compare, Data, Game, Quiz, Vote).",
    )
    parser.add_argument(
        "-p",
        "--presentation-id",
        dest="presentation_id",
        help="Optional live presentation ID to extract layouts from.",
    )
    parser.add_argument(
        "-l",
        "--layout",
        dest="layout_key",
        help="Inspect specific built-in layout preset key (e.g. 'intro_caption_hero').",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format.",
    )

    args = parser.parse_args()

    # Case 0: Dynamically List All Categories
    if args.list_categories:
        try:
            client = AhaApiClient()
            layouts = fetch_all_167_layouts(client=client)
            categories_map: dict[str, int] = {}
            for l in layouts:
                cat = str(l.get("category", "Uncategorized"))
                categories_map[cat] = categories_map.get(cat, 0) + 1
        except Exception as e:
            print(f"Error extracting categories: {e}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(categories_map, indent=2))
            return

        print("=== Dynamically Extracted Layout Categories ===")
        print(f"Total Unique Categories Found: {len(categories_map)}\n")
        for cat, count in sorted(categories_map.items(), key=lambda x: x[1], reverse=True):
            print(f"  • Category: {cat:<20} | Layout Count: {count}")
        return

    # Case 1: Fetch All Layouts Catalog
    if args.fetch_all or args.category:
        try:
            client = AhaApiClient()
            layouts = fetch_all_167_layouts(client=client)
        except Exception as e:
            print(f"Error fetching layout catalog: {e}", file=sys.stderr)
            sys.exit(1)

        if args.category:
            filtered = [l for l in layouts if str(args.category).lower() in str(l.get("category")).lower()]
            layouts = filtered

        if args.json:
            print(json.dumps(layouts, indent=2))
            return

        print("=== AhaSlides Layouts Catalog ===")
        print(f"Total Layouts Matched: {len(layouts)}")
        if args.category:
            print(f"Category Filter: '{args.category}'")
        print()
        for idx, item in enumerate(layouts):
            print(f"{idx + 1:03d}. [{item.get('category')}] {item.get('name')} (Source: {item.get('source')})")
        return

    # Case 2: Extract from Live Presentation
    if args.presentation_id:
        try:
            client = AhaApiClient()
            layouts = extract_layouts_from_presentation(args.presentation_id, client=client)
        except Exception as e:
            print(f"Error fetching presentation layout details: {e}", file=sys.stderr)
            sys.exit(1)

        if args.json:
            print(json.dumps(layouts, indent=2))
            return

        print(f"=== Presentation #{args.presentation_id} Slide Layouts ===")
        print(f"Total Slides: {len(layouts)}\n")
        for item in layouts:
            print(f"Slide #{item['slide_number']} (ID: {item['slide_id']})")
            print(f"  Type:          {item['slide_type']}")
            print(f"  Layout Prop:   {item['layout_property']}")
            print(f"  Has DSL:       {item['has_dsl']}")
            if item['has_dsl']:
                lines = item['dsl_text'].strip().split("\n")
                preview = "\n    ".join(lines[:6])
                print(f"  DSL Preview:\n    {preview}\n")
        return

    # Case 3: Inspect specific Builtin Preset
    if args.layout_key:
        if args.layout_key not in BUILTIN_LAYOUT_PRESETS:
            print(f"Error: Unknown layout preset '{args.layout_key}'.", file=sys.stderr)
            print(f"Available presets: {', '.join(BUILTIN_LAYOUT_PRESETS.keys())}", file=sys.stderr)
            sys.exit(1)

        preset = BUILTIN_LAYOUT_PRESETS[args.layout_key]
        if args.json:
            print(json.dumps(preset, indent=2))
            return

        print(f"=== Built-in Layout Preset: '{args.layout_key}' ===")
        print(f"Name:        {preset['name']}")
        print(f"Category:    {preset['category']}")
        print(f"Description: {preset['description']}")
        print(f"Elements:    {preset['elements_count']}\n")
        print("DSL Template:\n" + preset["dsl_template"])
        return

    # Default Case: List Builtin Presets
    if args.json:
        print(json.dumps(BUILTIN_LAYOUT_PRESETS, indent=2))
        return

    print("=== Built-in v2 DSL Layout Presets Registry ===")
    for key, preset in BUILTIN_LAYOUT_PRESETS.items():
        print(f"• Layout Key: '{key}'")
        print(f"  Name:        {preset['name']}")
        print(f"  Category:    {preset['category']}")
        print(f"  Description: {preset['description']}")
        print(f"  Elements:    {preset['elements_count']}\n")

    print("Tip: Run `python3 scripts/list_slide_layouts.py --all` (or `-a`) to view all layout templates.")
    print("Tip: Run `python3 scripts/list_slide_layouts.py --category Compare` to filter by category.")


if __name__ == "__main__":
    main()
