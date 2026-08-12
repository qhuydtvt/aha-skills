#!/usr/bin/env python3
"""Manage AhaSlides freestyle-v2 public slide templates and custom DSL templates.

Subcommands: list, categories, get, search, export, apply, stamp, create-from-template, save-from-slide, save-from-presentation (dump-presentation), lint-templates (lint).
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

from scripts.read_presentation import (
    parse_dsl_content,
)
from scripts.shared.api import AhaApiClient
from scripts.shared.lib.adsl_metadata import (
    embed_adsl_metadata,
    format_adsl_filename,
)

PUBLIC_TEMPLATES_PATH = "/api/slide/public-templates"
SLIDE_ATTRIBUTES_PATH = "/api/v2/slides/{slide_id}/attributes"
CDN_TIMEOUT_SECONDS = 10


def extract_slide_title(slide: dict[str, Any], dsl: str, index: int) -> str:
    """Extract and sanitize slide title from DSL content or slide metadata into a filename-safe format."""
    dsl_parsed = parse_dsl_content(dsl) if dsl else {}
    raw_title = (
        dsl_parsed.get("title")
        or slide.get("title")
        or slide.get("name")
        or slide.get("heading")
        or slide.get("question")
        or slide.get("sanitizedTitle")
        or ""
    )
    if not isinstance(raw_title, str):
        raw_title = str(raw_title) if raw_title is not None else ""

    clean = re.sub(r"[^a-z0-9]+", "_", raw_title.lower()).strip("_")
    clean = clean[:50].rstrip("_")

    if not clean:
        return f"slide_{index:02d}"
    return clean


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
    bg = _normalize_background_image(t.get("backgroundImage"))
    print(f"\n=== Template #{t.get('id')}: {t.get('title')} ===\nCategory:    {_get_category(t)}\nType:        {t.get('type', 'N/A')}\nThumbnail:   {t.get('contentTemplateThumbnail') or 'N/A'}\nBackground:  {bg or 'N/A'}\nCanvas URL:  {t.get('canvasBlocksUrl') or 'N/A'}\n")
    if args.canvas_blocks and t.get("canvasBlocksUrl"):
        content = _fetch_canvas_blocks(t["canvasBlocksUrl"])
        try:
            blocks = json.loads(content)
            print(f"Block count: {len(blocks)}")
            for bid, block in list(blocks.items())[:5]:
                print(f"  [{block.get('type', '?')}] id={bid} w={block.get('style',{}).get('width','?')}")
        except (json.JSONDecodeError, AttributeError):
            print(content[:500])


def cmd_search(args: argparse.Namespace, client: AhaApiClient) -> None:
    q = args.query.lower()
    matches = [t for t in _fetch_all_templates(client) if q in (t.get("title") or "").lower() or q in _get_category(t).lower()]
    if not matches:
        print(f"No templates matched '{args.query}'.")
        return
    if args.json:
        print(json.dumps(matches, indent=2))
        return
    print(f"\n=== Search Results for '{args.query}' ({len(matches)} found) ===\n")
    _print_table([(t.get("id", ""), _get_category(t), t.get("title", "")) for t in matches], ["ID", "Category", "Name"])
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
    print(f"Exported template #{t.get('id')} ({t.get('title')}) → {out_path} ({size_kb:.1f} KB)")


def cmd_apply(args: argparse.Namespace, client: AhaApiClient) -> None:
    t = _find_template(args.template_id, client)
    url = t.get("canvasBlocksUrl")
    if not url:
        print(f"[ERROR] Template #{t.get('id')} has no canvasBlocksUrl.", file=sys.stderr)
        sys.exit(1)
    dsl_text = _fetch_canvas_blocks(url)
    if args.dry_run:
        print(f"\n--- Dry Run: DSL for template #{t.get('id')} ({t.get('title')}) → slide {args.slide} ---\n{dsl_text[:1000]}")
        return
    result = _apply_canvas_blocks_to_slide(args.slide, url, getattr(args, "presentation", 0), client)
    if args.json:
        print(json.dumps({"template_id": t.get("id"), "slide_id": args.slide, "result": result}))
        return
    print(f"\n=== Apply Template ===\nTemplate: #{t.get('id')} ({t.get('title')})\nSlide:    {args.slide}\nStatus:   ✅ DSL applied\n")


def cmd_stamp(args: argparse.Namespace, client: AhaApiClient) -> None:
    t = _find_template(args.template_id, client)
    bg = _normalize_background_image(t.get("backgroundImage"))
    if not bg:
        print(f"[ERROR] Template #{t.get('id')} has no background image.", file=sys.stderr)
        sys.exit(1)
    from scripts.update_slide import update_slide
    update_slide(slide_id=args.slide, background_image=bg, apply_to_all=args.apply_to_all, client=client)
    if args.json:
        print(json.dumps({"template_id": t.get("id"), "slide_id": args.slide, "background_image": bg}))
        return
    print(f"\n=== Stamp Background ===\nTemplate:   #{t.get('id')} ({t.get('title')})\nBackground: {bg}\nSlide:      {args.slide}\nStatus:     ✅ applied\n")


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
    _apply_canvas_blocks_to_slide(new_slide_id, url, args.presentation, client)
    if args.json:
        print(json.dumps({"template_id": t.get("id"), "presentation_id": args.presentation, "new_slide_id": new_slide_id}))
        return
    print(f"\n=== Create From Template ===\nTemplate:     #{t.get('id')} ({t.get('title')})\nPresentation: {args.presentation}\nNew Slide ID: {new_slide_id}\nStatus:       ✅ success\n")


def cmd_save_from_slide(args: argparse.Namespace, client: AhaApiClient) -> None:
    sid = str(args.slide_id)
    res = client.get("/api/v2/slides/attributes", params={"slideIds": sid})
    dsl = ""
    pres_id = None
    if isinstance(res, list):
        for item in res:
            if str(item.get("slideId")) == sid or len(res) == 1:
                pres_id = item.get("presentationId")
                attrs = item.get("attributes", {})
                dsl = attrs if isinstance(attrs, str) else attrs.get("dsl", "")
                break
    if not dsl:
        print(f"[ERROR] Slide {sid} has no DSL attribute content.", file=sys.stderr)
        sys.exit(1)

    dsl = embed_adsl_metadata(dsl, pres_id, sid)
    out_name = args.name or format_adsl_filename(f"slide_{sid}", pres_id, sid)
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
    print(f"\n=== Save Template From Slide ===\nSlide ID: {sid}\nSaved To: {out_path} ({len(dsl)} bytes)\nStatus:   ✅ success\n")


def cmd_save_from_presentation(args: argparse.Namespace, client: AhaApiClient) -> None:
    from scripts.shared.lib.adsl_metadata import save_presentation_templates

    res = save_presentation_templates(
        client=client,
        presentation_id=args.presentation_id,
        output_dir=args.output_dir,
        pattern=args.pattern,
        slides_filter=getattr(args, "slides", None),
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        json_output=args.json,
    )
    if args.json:
        print(json.dumps(res, indent=2))
        return

    mode_str = " (Dry Run)" if args.dry_run else ""
    print(f"\n=== Save Presentation Templates{mode_str} ===")
    print(f"Presentation ID:  {args.presentation_id}")
    print(f"Output Directory: {args.output_dir}")
    slides = res.get("slides", [])
    print(f"Slides Processed: {len(slides)}\n")
    rows = [(s["index"], s["slide_id"], s["filename"], f"{s['size_bytes']} B", s["status"]) for s in slides]
    _print_table(rows, ["Index", "Slide ID", "Filename", "Size", "Status"])
    print()


def cmd_lint_templates(args: argparse.Namespace, client: AhaApiClient) -> None:
    from scripts.shared.lib.adsl_metadata import lint_adsl_files

    files: list[Path] = []
    if getattr(args, "file", None):
        fp = Path(args.file)
        if not fp.is_file():
            print(f"[ERROR] File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        files.append(fp)
    else:
        dp = Path(getattr(args, "dir", "artifacts/dsl-templates"))
        if not dp.is_dir():
            print(f"[ERROR] Directory not found: {dp}", file=sys.stderr)
            sys.exit(1)
        files = sorted(dp.glob("*.adsl"))

    report = lint_adsl_files(files)
    if args.json:
        print(json.dumps(report, indent=2))
        if not report["valid"]:
            sys.exit(1)
        return

    print("\n=== ADSL Template Metadata Linter ===")
    print(f"Total Files:  {report['total_files']}\nPassed:       {report['passed_count']}\nFailed:       {report['failed_count']}\nTotal Errors: {report['total_errors']}\n")

    if not report["valid"]:
        print("Linting Failures:")
        for r in report["results"]:
            if not r["valid"]:
                print(f"  ❌ {r['filename']}:")
                for err in r["errors"]:
                    print(f"     - {err}")
        print()
        sys.exit(1)
    print("✅ All ADSL templates passed metadata linting cleanly with 0 errors!\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="manage_slide_template",
        description="Manage AhaSlides freestyle-v2 public slide templates and custom DSL templates.",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON.")
    subparsers = parser.add_subparsers(dest="verb", required=True, metavar="VERB")

    p_list = subparsers.add_parser("list", help="Browse all public templates.")
    p_list.add_argument("-c", "--category", help="Filter by category substring.")
    p_list.add_argument("-n", "--limit", type=int, help="Cap output at N items.")

    subparsers.add_parser("categories", help="List unique category names with counts.")

    p_get = subparsers.add_parser("get", help="Inspect a single template by ID.")
    p_get.add_argument("template_id", help="Numeric public template ID.")
    p_get.add_argument("--canvas-blocks", action="store_true", dest="canvas_blocks", help="Fetch canvas blocks.")

    p_search = subparsers.add_parser("search", help="Substring-search templates.")
    p_search.add_argument("query", help="Search string.")

    p_export = subparsers.add_parser("export", help="Download canvas-blocks JSON.")
    p_export.add_argument("template_id", help="Numeric template ID.")
    p_export.add_argument("-o", "--output", help="Output file path.")

    p_apply = subparsers.add_parser("apply", help="Apply template DSL to slide.")
    p_apply.add_argument("template_id", help="Numeric template ID.")
    p_apply.add_argument("--slide", required=True, help="Target slide ID.")
    p_apply.add_argument("--dry-run", action="store_true", dest="dry_run", help="Preview DSL.")

    p_stamp = subparsers.add_parser("stamp", help="Apply background image.")
    p_stamp.add_argument("template_id", help="Numeric template ID.")
    p_stamp.add_argument("--slide", required=True, help="Target slide ID.")
    p_stamp.add_argument("--apply-to-all", action="store_true", dest="apply_to_all", help="Apply to all slides.")

    p_cft = subparsers.add_parser("create-from-template", help="Create slide & apply template.")
    p_cft.add_argument("template_id", help="Numeric template ID.")
    p_cft.add_argument("--presentation", required=True, help="Presentation ID.")

    p_sfs = subparsers.add_parser("save-from-slide", help="Save live slide DSL.")
    p_sfs.add_argument("slide_id", help="Slide ID.")
    p_sfs.add_argument("--name", help="Template filename.")
    p_sfs.add_argument("-o", "--output", help="Output path.")

    p_sfp = subparsers.add_parser("save-from-presentation", aliases=["dump-presentation"], help="Save presentation slides DSL.")
    p_sfp.add_argument("presentation_id", help="Presentation ID.")
    p_sfp.add_argument("-o", "--output-dir", default="artifacts/dsl-templates", help="Output dir.")
    p_sfp.add_argument("--pattern", default="{title}_{presentation_id}_{slide_id}.adsl", help="Filename pattern.")
    p_sfp.add_argument("-s", "--slides", help="Filter slides.")
    p_sfp.add_argument("-f", "--overwrite", action="store_true", help="Overwrite existing.")
    p_sfp.add_argument("--dry-run", action="store_true", dest="dry_run", help="Preview without writing.")
    p_sfp.add_argument("--json", action="store_true", help="Output JSON.")

    p_lint = subparsers.add_parser("lint-templates", aliases=["lint"], help="Lint ADSL template metadata.")
    p_lint.add_argument("--dir", default="artifacts/dsl-templates", help="Templates directory.")
    p_lint.add_argument("--file", help="Single template file.")
    p_lint.add_argument("--json", action="store_true", help="Output JSON.")

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
        "save-from-presentation": cmd_save_from_presentation,
        "dump-presentation": cmd_save_from_presentation,
        "lint-templates": cmd_lint_templates,
        "lint": cmd_lint_templates,
    }

    try:
        dispatch[args.verb](args, client)
    except (ValueError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
