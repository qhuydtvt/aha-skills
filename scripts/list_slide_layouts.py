from __future__ import annotations
#!/usr/bin/env python3
"""Script to list and inspect slide layout templates and v2 DSL structures.

Supports:
1. Listing pre-built v2 DSL layout presets (content-v2: intro_caption_hero, grid_3cards, etc.).
2. Fetching and browsing the full freestyle-v2 public templates library (128 layouts) grouped by
   category (Fun, Work, School, Holidays, …) via --sub-categories or --type freestyle-v2.
3. Fetching raw DSL/canvas-blocks from any freestyle-v2 public template via --fetch-dsl.
4. Extracting layout DSL templates directly from any live presentation ID.

Usage:
    python3 scripts/list_slide_layouts.py
    python3 scripts/list_slide_layouts.py --all
    python3 scripts/list_slide_layouts.py --type content-v2
    python3 scripts/list_slide_layouts.py --type freestyle-v2 --limit 20
    python3 scripts/list_slide_layouts.py --sub-categories
    python3 scripts/list_slide_layouts.py --all --sub-categories
    python3 scripts/list_slide_layouts.py --fetch-dsl <template_id>
    python3 scripts/list_slide_layouts.py --category Content
    python3 scripts/list_slide_layouts.py -p <presentation_id>
    python3 scripts/list_slide_layouts.py --layout intro_caption_hero
    python3 scripts/list_slide_layouts.py --json
"""

import argparse
import json
import sys
import urllib.request
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
    },
    "title_body": {
        "name": "05 Title and Body",
        "category": "Content",
        "description": "Standard slide with a top title and a large body text area.",
        "elements_count": 2,
        "dsl_template": """---
content-v2: 1280x720
version: 1
---

:::text id={id_title} at=top-left width=1120 height=88 offsetX=80 offsetY=80 preset=title align=left color=text fontSize=56
{title_text}
:::

:::text id={id_body} at=top-left width=1120 height=400 offsetX=80 offsetY=200 preset=body align=left color=text
{body_text}
:::
"""
    },
    "hero_image": {
        "name": "06 Hero Image Left, Title & Body Right",
        "category": "Content",
        "description": "Left half is an image, right half is title and body.",
        "elements_count": 3,
        "dsl_template": """---
content-v2: 1280x720
version: 1
---

:::image id={id_image} at=center offsetX=-300 offsetY=0 width=500 height=500 objectFit=cover
:::

:::text id={id_title} at=top-left width=500 height=88 offsetX=680 offsetY=120 preset=title align=left color=text fontSize=48
{title_text}
:::

:::text id={id_body} at=top-left width=500 height=300 offsetX=680 offsetY=240 preset=body align=left color=text
{body_text}
:::
"""
    },
    "two_column_text": {
        "name": "07 Two Column Text",
        "category": "Content",
        "description": "Title centered, with two columns of text.",
        "elements_count": 3,
        "dsl_template": """---
content-v2: 1280x720
version: 1
---

:::text id={id_title} at=center width=85% offsetX=0 offsetY=-240 preset=title color=text
{title_text}
:::

:::text id={id_left} at=center width=40% offsetX=-280 offsetY=0 preset=body color=text align=left
{left_text}
:::

:::text id={id_right} at=center width=40% offsetX=280 offsetY=0 preset=body color=text align=left
{right_text}
:::
"""
    },
    "quote": {
        "name": "08 Big Quote",
        "category": "Visual",
        "description": "Large quote with author attribution.",
        "elements_count": 2,
        "dsl_template": """---
content-v2: 1280x720
version: 1
---

:::text id={id_quote} at=center width=800 height=300 offsetX=0 offsetY=-50 preset=title align=center color=text fontSize=48 fontStyle=italic
"{quote_text}"
:::

:::text id={id_author} at=center width=400 height=60 offsetX=0 offsetY=150 preset=body align=center color=muted fontSize=24
— {author_text}
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
                    "canvas_blocks_url": item.get("canvasBlocksUrl"),
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


def fetch_freestyle_dsl(template_id: str, client: AhaApiClient | None = None) -> str:
    """Fetch raw DSL/canvas-blocks for a freestyle-v2 public template by its ID.

    Looks up the template in /api/slide/public-templates, resolves its
    canvasBlocksUrl, and returns the raw DSL text.
    """
    if client is None:
        client = AhaApiClient()
    pub_res = client.get(PUBLIC_TEMPLATES_PATH)
    if not isinstance(pub_res, list):
        raise ValueError("Unexpected response from public-templates API")
    for item in pub_res:
        if str(item.get("id")) == str(template_id):
            url = item.get("canvasBlocksUrl")
            if not url:
                raise ValueError(f"Template {template_id} has no canvasBlocksUrl")
            with urllib.request.urlopen(url) as resp:  # noqa: S310
                return resp.read().decode("utf-8")
    raise ValueError(f"Template ID '{template_id}' not found in public-templates")


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
        "--type",
        "-t",
        dest="slide_type",
        help="Filter layouts by slide type (e.g. content-v2, freestyle-v2, wordCloud).",
    )
    parser.add_argument(
        "--sub-categories",
        action="store_true",
        help="Show built-in presets alongside API layouts grouped by type and category. "
             "content-v2 items are listed individually; large types (e.g. freestyle-v2) show a "
             "compact category summary. Combine with --all to expand all items.",
    )
    parser.add_argument(
        "--fetch-dsl",
        dest="fetch_dsl_id",
        metavar="TEMPLATE_ID",
        help="Fetch and print the raw DSL from a freestyle-v2 public template by its numeric ID "
             "(resolves canvasBlocksUrl and downloads the canvas-blocks file).",
    )
    parser.add_argument(
        "--limit",
        "-n",
        dest="limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap the number of layouts shown in list output (e.g. --limit 20).",
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
    if args.fetch_all or args.category or args.slide_type:
        try:
            client = AhaApiClient()
            layouts = fetch_all_167_layouts(client=client)
        except Exception as e:
            print(f"Error fetching layout catalog: {e}", file=sys.stderr)
            sys.exit(1)

        # Always inject built-in content-v2 presets so --type content-v2 returns results
        for key, preset in BUILTIN_LAYOUT_PRESETS.items():
            layouts.append({
                "id": key,
                "name": preset["name"],
                "type": "content-v2",
                "category": preset["category"],
                "source": "builtin-presets",
            })

        if args.category:
            layouts = [l for l in layouts if str(args.category).lower() in str(l.get("category")).lower()]

        if args.slide_type:
            # Support alias: freestyle-v2 <-> freestyle
            req = args.slide_type.lower()
            aliases = {req}
            if req == "freestyle-v2":
                aliases.add("freestyle")
            elif req == "freestyle":
                aliases.add("freestyle-v2")
            layouts = [l for l in layouts if str(l.get("type", "")).lower() in aliases]

        if args.limit is not None:
            layouts = layouts[:args.limit]

        if args.json:
            print(json.dumps(layouts, indent=2))
            return

        print("=== AhaSlides Layouts Catalog ===")
        print(f"Total Layouts Matched: {len(layouts)}")
        if args.category:
            print(f"Category Filter: '{args.category}'")
        if args.slide_type:
            print(f"Type Filter: '{args.slide_type}'")
        if args.limit is not None:
            print(f"Limit: {args.limit}")
        print()
        for idx, item in enumerate(layouts):
            print(f"{idx + 1:03d}. [{item.get('type')}] [{item.get('category')}] {item.get('name')} (Source: {item.get('source')})")
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

    # Case 4: Sub-categories
    if args.sub_categories:
        try:
            client = AhaApiClient()
            layouts = fetch_all_167_layouts(client=client)
        except Exception as e:
            print(f"Error fetching layout catalog: {e}", file=sys.stderr)
            sys.exit(1)

        # Add built-in content-v2 presets
        for key, preset in BUILTIN_LAYOUT_PRESETS.items():
            layouts.append({
                "id": key,
                "name": preset["name"],
                "type": "content-v2",
                "category": preset["category"],
                "source": "builtin-presets",
            })

        # Group by type then category
        grouped: dict[str, dict[str, list]] = {}
        for l in layouts:
            t = str(l.get("type", "Unknown"))
            c = str(l.get("category", "Uncategorized"))
            if t not in grouped:
                grouped[t] = {}
            if c not in grouped[t]:
                grouped[t][c] = []
            grouped[t][c].append(l)

        if args.json:
            print(json.dumps(grouped, indent=2))
            return

        # When --all is also passed, show every item; otherwise compact large types
        expand_all = args.fetch_all
        # Types with few items (content-v2, marketplace) are always expanded
        COMPACT_THRESHOLD = 20

        print("=== AhaSlides Layouts by Type & Category ===")
        for t in sorted(grouped.keys()):
            type_total = sum(len(v) for v in grouped[t].values())
            print(f"\nType: {t}  ({type_total} layouts)")
            for c in sorted(grouped[t].keys()):
                items_in_cat = grouped[t][c]
                print(f"  Category: {c} ({len(items_in_cat)})")
                if expand_all or type_total <= COMPACT_THRESHOLD:
                    # Full listing
                    for l in sorted(items_in_cat, key=lambda x: x["name"]):
                        print(f"    - {l['name']} (ID: {l['id']}, Source: {l['source']})")
                else:
                    # Compact preview: first 4 names + overflow count
                    names = sorted(x["name"] for x in items_in_cat)
                    preview = ", ".join(names[:4])
                    if len(names) > 4:
                        preview += f", … (+{len(names) - 4} more)"
                    print(f"    ↳ {preview}")
        if not expand_all:
            print("\nTip: Add --all to expand all items in every category.")
        return

    # Case 4b: Fetch DSL from a freestyle-v2 public template
    if args.fetch_dsl_id:
        try:
            client = AhaApiClient()
            dsl = fetch_freestyle_dsl(args.fetch_dsl_id, client=client)
        except Exception as e:
            print(f"Error fetching DSL for template '{args.fetch_dsl_id}': {e}", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps({"template_id": args.fetch_dsl_id, "dsl": dsl}, indent=2))
        else:
            print(f"=== DSL for freestyle-v2 Template #{args.fetch_dsl_id} ===\n")
            print(dsl)
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
    print("Tip: Run `python3 scripts/list_slide_layouts.py --type freestyle-v2 --sub-categories` to browse freestyle-v2 by category.")
    print("Tip: Run `python3 scripts/list_slide_layouts.py --fetch-dsl <id>` to inspect a freestyle-v2 template's DSL.")
    print("Tip: Run `python3 scripts/list_slide_layouts.py --category Compare` to filter by category.")


if __name__ == "__main__":
    main()
