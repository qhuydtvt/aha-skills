#!/usr/bin/env python3
"""Manage AhaSlides freestyle-v2 public slide templates.

Subcommands:
  list                  Browse all public templates (with optional filters)
  categories            List unique category names with counts
  get                   Inspect a single template's metadata and canvas blocks
  search                Substring-search templates by name or category
  export                Download canvas-blocks JSON to a local file
  apply                 Apply a template's canvas-blocks DSL to an existing slide
  stamp                 Apply only the template's background image to a slide
  create-from-template  Create a new slide and immediately apply a template

Usage examples:
    python3 scripts/manage_slide_template.py list
    python3 scripts/manage_slide_template.py list --category Fun --limit 10
    python3 scripts/manage_slide_template.py categories
    python3 scripts/manage_slide_template.py get 135119967
    python3 scripts/manage_slide_template.py get 135119967 --canvas-blocks
    python3 scripts/manage_slide_template.py search "holiday"
    python3 scripts/manage_slide_template.py export 135119967 -o my_template.json
    python3 scripts/manage_slide_template.py apply 135119967 --slide 157058435
    python3 scripts/manage_slide_template.py apply 135119967 --slide 157058435 --dry-run
    python3 scripts/manage_slide_template.py stamp 135119967 --slide 157058435
    python3 scripts/manage_slide_template.py create-from-template 135119967 --presentation 9840079
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

PUBLIC_TEMPLATES_PATH = "/api/slide/public-templates"
SLIDE_ATTRIBUTES_PATH = "/api/v2/slides/{slide_id}/attributes"
CDN_TIMEOUT_SECONDS = 10


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _fetch_all_templates(client: AhaApiClient) -> list[dict[str, Any]]:
    """Fetch all public templates from the API."""
    res = client.get(PUBLIC_TEMPLATES_PATH)
    if not isinstance(res, list):
        raise TypeError(f"Unexpected response from public-templates API: {type(res)}")
    return res


def _find_template(template_id: str | int, client: AhaApiClient) -> dict[str, Any]:
    """Lookup a single template by ID. Raises ValueError if not found."""
    for item in _fetch_all_templates(client):
        if str(item.get("id")) == str(template_id):
            return item
    raise ValueError(f"Template ID '{template_id}' not found in public-templates")


def _get_category(template: dict[str, Any]) -> str:
    """The 'title' field in public-templates IS the category (Fun, Work, School, Holidays, etc.)."""
    return template.get("title") or "Uncategorized"


def _get_thumb_index(template: dict[str, Any]) -> str:
    """Extract a sequential index from the CDN thumbnail URL path, e.g. Fun/12.png -> 12."""
    thumb = template.get("contentTemplateThumbnail") or ""
    m = re.search(r"/([^/]+\.png)$", thumb)
    return m.group(1) if m else ""


def _fetch_canvas_blocks(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=CDN_TIMEOUT_SECONDS) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to fetch canvas blocks from CDN: {exc}") from exc


def _normalize_background_image(bg: Any) -> str | None:
    if not bg:
        return None
    if isinstance(bg, dict):
        return bg.get("url") or bg.get("thumbnail")
    return str(bg)


def _apply_canvas_blocks_to_slide(
    slide_id: str | int, canvas_blocks_url: str, presentation_id: str | int, client: AhaApiClient
) -> dict[str, Any]:
    """Apply a template to a freestyle-v2 slide by setting its canvasBlocksUrl field.
    
    The freestyle-v2 renderer fetches blocks at render time from canvasBlocksUrl.
    This is the correct mechanism — the attributes endpoint (dsl/canvasBlocks) is NOT read by the renderer.
    """
    return client.patch("/api/slide/", json_data={
        "presentationId": int(presentation_id),
        "slides": [{"id": int(slide_id), "canvasBlocksUrl": canvas_blocks_url}],
    })


def _print_table(rows: list, headers: list[str]) -> None:
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    sep = "  ".join("-" * w for w in col_widths)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))


# ---------------------------------------------------------------------------
# Verb implementations
# ---------------------------------------------------------------------------

def cmd_list(args: argparse.Namespace, client: AhaApiClient) -> None:
    templates = _fetch_all_templates(client)
    if getattr(args, "category", None):
        templates = [t for t in templates if args.category.lower() in _get_category(t).lower()]
    if getattr(args, "limit", None):
        templates = templates[: args.limit]

    if args.json:
        print(json.dumps(templates, indent=2))
        return

    print(f"\n=== Public Freestyle Templates ({len(templates)} shown) ===\n")
    rows = [
        (i, t.get("id", ""), _get_category(t), _get_thumb_index(t))
        for i, t in enumerate(templates, 1)
    ]
    _print_table(rows, ["#", "ID", "Category", "Index"])
    print()


def cmd_categories(args: argparse.Namespace, client: AhaApiClient) -> None:
    templates = _fetch_all_templates(client)
    counts: dict[str, int] = {}
    for t in templates:
        cat = _get_category(t)
        counts[cat] = counts.get(cat, 0) + 1
    sorted_cats = sorted(counts.items(), key=lambda x: -x[1])

    if args.json:
        print(json.dumps(dict(sorted_cats), indent=2))
        return

    print(f"\n=== Template Categories ({len(counts)} total) ===\n")
    _print_table(sorted_cats, ["Category", "Count"])
    print()


def cmd_get(args: argparse.Namespace, client: AhaApiClient) -> None:
    t = _find_template(args.template_id, client)

    if args.json:
        result: dict[str, Any] = dict(t)
        if args.canvas_blocks:
            url = t.get("canvasBlocksUrl")
            result["canvasBlocksContent"] = _fetch_canvas_blocks(url) if url else None
        print(json.dumps(result, indent=2))
        return

    print(f"\n=== Template #{t.get('id')}: {t.get('title')} ===")
    print(f"Category:    {_get_category(t)}")
    print(f"Type:        {t.get('type', 'N/A')}")
    print(f"Thumbnail:   {t.get('contentTemplateThumbnail') or 'N/A'}")
    bg = _normalize_background_image(t.get("backgroundImage"))
    print(f"Background:  {bg or 'N/A'}")
    canvas_url = t.get("canvasBlocksUrl") or ""
    print(f"Canvas URL:  {canvas_url or 'N/A'}")

    if args.canvas_blocks:
        if not canvas_url:
            print("\n[WARNING] Template has no canvasBlocksUrl.")
        else:
            content = _fetch_canvas_blocks(canvas_url)
            try:
                blocks = json.loads(content)
                print(f"\nBlock count: {len(blocks)}")
                for bid, block in list(blocks.items())[:5]:
                    btype = block.get("type", "?")
                    style = block.get("style", {})
                    print(f"  [{btype}] id={bid}  w={style.get('width','?')} h={style.get('height','?')} transform={style.get('transform','?')}")
                if len(blocks) > 5:
                    print(f"  … and {len(blocks) - 5} more blocks")
            except (json.JSONDecodeError, AttributeError):
                print(content[:1000])
    print()


def cmd_search(args: argparse.Namespace, client: AhaApiClient) -> None:
    q = args.query.lower()
    matches = [
        t for t in _fetch_all_templates(client)
        if q in (t.get("title") or "").lower() or q in _get_category(t).lower()
    ]

    if not matches:
        print(f"No templates matched '{args.query}'.")
        return

    if args.json:
        print(json.dumps(matches, indent=2))
        return

    print(f"\n=== Search Results for '{args.query}' ({len(matches)} found) ===\n")
    _print_table(
        [(t.get("id", ""), _get_category(t), t.get("title", "")) for t in matches],
        ["ID", "Category", "Name"],
    )
    print()


def cmd_export(args: argparse.Namespace, client: AhaApiClient) -> None:
    t = _find_template(args.template_id, client)
    url = t.get("canvasBlocksUrl")
    if not url:
        print(f"[ERROR] Template #{t.get('id')} has no canvas blocks to export.", file=sys.stderr)
        sys.exit(1)

    content = _fetch_canvas_blocks(url)
    out_path = Path(args.output) if args.output else Path(f"template_{t.get('id')}.json")
    out_path.write_text(content, encoding="utf-8")
    size_kb = out_path.stat().st_size / 1024

    if args.json:
        print(json.dumps({"template_id": t.get("id"), "output": str(out_path), "size_kb": round(size_kb, 1)}))
        return
    print(f"Exported template #{t.get('id')} ({t.get('title')}) → {out_path}  ({size_kb:.1f} KB)")


def cmd_apply(args: argparse.Namespace, client: AhaApiClient) -> None:
    t = _find_template(args.template_id, client)
    url = t.get("canvasBlocksUrl")
    if not url:
        print(f"[ERROR] Template #{t.get('id')} has no canvasBlocksUrl.", file=sys.stderr)
        sys.exit(1)

    dsl_text = _fetch_canvas_blocks(url)

    if ":::" not in dsl_text:
        print("[WARNING] Canvas content has no ':::' DSL markers — this is raw canvas-blocks JSON.")
        print("          Slide must be type=freestyle-v2 to render this content correctly.")

    if args.dry_run:
        print(f"\n--- Dry Run: DSL for template #{t.get('id')} ({t.get('title')}) → slide {args.slide} ---\n")
        print(dsl_text[:3000])
        if len(dsl_text) > 3000:
            print(f"\n… (truncated, {len(dsl_text)} total chars)")
        return

    result = _apply_canvas_blocks_to_slide(args.slide, dsl_text, client)

    if args.json:
        print(json.dumps({"template_id": t.get("id"), "slide_id": args.slide, "result": result}))
        return

    print("\n=== Apply Template ===")
    print(f"Template:  #{t.get('id')} ({t.get('title')})")
    print(f"Slide:     {args.slide}")
    print("Status:    ✅ DSL applied")
    print()


def cmd_stamp(args: argparse.Namespace, client: AhaApiClient) -> None:
    t = _find_template(args.template_id, client)
    bg = _normalize_background_image(t.get("backgroundImage"))
    if not bg:
        print(f"[ERROR] Template #{t.get('id')} has no background image.", file=sys.stderr)
        sys.exit(1)

    from scripts.update_slide import update_slide
    update_slide(slide_id=args.slide, background_image=bg, apply_to_all=args.apply_to_all, client=client)

    if args.json:
        print(json.dumps({"template_id": t.get("id"), "slide_id": args.slide, "background_image": bg, "apply_to_all": args.apply_to_all}))
        return

    print("\n=== Stamp Background ===")
    print(f"Template:      #{t.get('id')} ({t.get('title')})")
    print(f"Background:    {bg}")
    print(f"Slide:         {args.slide}")
    print(f"Apply to All:  {args.apply_to_all}")
    print("Status:        ✅ background image applied")
    print()


def cmd_create_from_template(args: argparse.Namespace, client: AhaApiClient) -> None:
    t = _find_template(args.template_id, client)
    url = t.get("canvasBlocksUrl")
    if not url:
        print(f"[ERROR] Template #{t.get('id')} has no canvasBlocksUrl.", file=sys.stderr)
        sys.exit(1)

    from scripts.create_slide import create_slide
    res = create_slide(presentation_id=args.presentation, slide_type="freestyle-v2", at_end=True)
    new_slide_id = (res.get("id") or res.get("_id")) if isinstance(res, dict) else None
    if not new_slide_id:
        print(f"[ERROR] Slide creation failed: {res}", file=sys.stderr)
        sys.exit(1)

    print(f"Created slide #{new_slide_id} (type: freestyle-v2) in presentation {args.presentation}")

    # Set canvasBlocksUrl on the new slide — the freestyle-v2 renderer reads this at render time
    _apply_canvas_blocks_to_slide(new_slide_id, url, args.presentation, client)

    if args.json:
        print(json.dumps({
            "template_id": t.get("id"),
            "template_name": t.get("title"),
            "presentation_id": args.presentation,
            "new_slide_id": new_slide_id,
            "dsl_applied": True,
        }))
        return

    print("\n=== Create From Template ===")
    print(f"Template:      #{t.get('id')} ({t.get('title')})")
    print(f"Presentation:  {args.presentation}")
    print(f"New Slide ID:  {new_slide_id}")
    print("DSL Applied:   ✅")
    print("Status:        ✅ success")
    print()


def cmd_save_from_slide(args: argparse.Namespace, client: AhaApiClient) -> None:
    sid = str(args.slide_id)
    res = client.get("/api/v2/slides/attributes", params={"slideIds": sid})
    dsl = ""
    if isinstance(res, list):
        for item in res:
            if str(item.get("slideId")) == sid or len(res) == 1:
                attrs = item.get("attributes", {})
                if isinstance(attrs, str):
                    dsl = attrs
                elif isinstance(attrs, dict):
                    dsl = attrs.get("dsl", "")
                break
    elif isinstance(res, dict) and sid in res:
        attrs = res[sid].get("attributes", {})
        if isinstance(attrs, str):
            dsl = attrs
        elif isinstance(attrs, dict):
            dsl = attrs.get("dsl", "")

    if not dsl:
        print(f"[ERROR] Slide {sid} has no DSL attribute content.", file=sys.stderr)
        sys.exit(1)

    out_name = args.name if args.name else f"{sid}.adsl"
    if not out_name.endswith(".adsl") and not out_name.endswith(".dsl"):
        out_name += ".adsl"

    out_dir = Path("artifacts/dsl-templates")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.output) if args.output else (out_dir / out_name)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dsl, encoding="utf-8")

    if args.json:
        print(json.dumps({"slide_id": sid, "output": str(out_path), "size_bytes": len(dsl)}))
        return

    print("\n=== Save Template From Slide ===")
    print(f"Slide ID:   {sid}")
    print(f"Saved To:   {out_path} ({len(dsl)} bytes)")
    print("Status:     ✅ success")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="manage_slide_template",
        description="Manage AhaSlides freestyle-v2 public slide templates and custom DSL templates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON.")
    subparsers = parser.add_subparsers(dest="verb", required=True, metavar="VERB")

    p_list = subparsers.add_parser("list", help="Browse all public templates.")
    p_list.add_argument("-c", "--category", help="Filter by category substring.")
    p_list.add_argument("-n", "--limit", type=int, help="Cap output at N items.")

    subparsers.add_parser("categories", help="List unique category names with counts.")

    p_get = subparsers.add_parser("get", help="Inspect a single template by ID.")
    p_get.add_argument("template_id", help="Numeric public template ID.")
    p_get.add_argument("--canvas-blocks", action="store_true", dest="canvas_blocks", help="Also fetch and summarize canvas-blocks content.")

    p_search = subparsers.add_parser("search", help="Substring-search templates by name or category.")
    p_search.add_argument("query", help="Case-insensitive search string.")

    p_export = subparsers.add_parser("export", help="Download canvas-blocks JSON to a local file.")
    p_export.add_argument("template_id", help="Numeric public template ID.")
    p_export.add_argument("-o", "--output", help="Output file path (default: template_{id}.json).")

    p_apply = subparsers.add_parser("apply", help="Apply a template's DSL to an existing slide.")
    p_apply.add_argument("template_id", help="Numeric public template ID.")
    p_apply.add_argument("--slide", required=True, help="Target slide ID.")
    p_apply.add_argument("--dry-run", action="store_true", dest="dry_run", help="Print resolved DSL without mutating.")

    p_stamp = subparsers.add_parser("stamp", help="Apply only the template background image to a slide.")
    p_stamp.add_argument("template_id", help="Numeric public template ID.")
    p_stamp.add_argument("--slide", required=True, help="Target slide ID.")
    p_stamp.add_argument("--apply-to-all", action="store_true", dest="apply_to_all", help="Apply background to ALL slides in the presentation.")

    p_cft = subparsers.add_parser("create-from-template", help="Create a new slide and immediately apply a template.")
    p_cft.add_argument("template_id", help="Numeric public template ID.")
    p_cft.add_argument("--presentation", required=True, help="Target presentation ID.")

    p_sfs = subparsers.add_parser("save-from-slide", help="Dump and save a live slide's DSL content into artifacts/dsl-templates/.")
    p_sfs.add_argument("slide_id", help="Target live slide ID.")
    p_sfs.add_argument("--name", help="Template filename/identifier (default: {slide_id}.adsl).")
    p_sfs.add_argument("-o", "--output", help="Explicit output file path.")

    args = parser.parse_args()
    if not hasattr(args, "json"):
        args.json = False

    client = AhaApiClient()

    dispatch = {
        "list": cmd_list,
        "categories": cmd_categories,
        "get": cmd_get,
        "search": cmd_search,
        "export": cmd_export,
        "apply": cmd_apply,
        "stamp": cmd_stamp,
        "create-from-template": cmd_create_from_template,
        "save-from-slide": cmd_save_from_slide,
    }

    try:
        dispatch[args.verb](args, client)
    except (ValueError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
