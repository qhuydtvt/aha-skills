#!/usr/bin/env python3
"""Script to apply vendor-independent layout presets or layout DSLs to live slides on AhaSlides."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.lint_slide import lint_slide
from scripts.list_slide_elements import list_slide_elements
from scripts.list_slide_layouts import BUILTIN_LAYOUT_PRESETS
from scripts.read_slide import read_slide
from scripts.shared.api import AhaApiClient

SLIDE_ATTRIBUTES_PATH = "/api/v2/slides/attributes"
UPDATE_ATTRIBUTES_PATH = "/api/v2/slides/{slide_id}/attributes"
PUBLIC_TEMPLATES_PATH = "/api/slide/public-templates"


def resolve_layout_dsl(
    client: AhaApiClient,
    layout_key: str | None = None,
    source_slide_id: str | None = None,
    template_id: str | None = None,
    dsl_file: str | None = None,
) -> tuple[str, str]:
    """Resolve raw layout DSL template and source description from specified layout option.

    Enforces that exactly ONE layout source is specified.
    """
    sources = [
        ("layout_key", layout_key),
        ("source_slide_id", source_slide_id),
        ("template_id", template_id),
        ("dsl_file", dsl_file),
    ]
    provided = [name for name, val in sources if val is not None]

    if len(provided) == 0:
        raise ValueError(
            "Must specify exactly one layout source: -l/--layout, -s/--source-slide, -t/--template-id, or -f/--dsl-file"
        )
    if len(provided) > 1:
        raise ValueError(
            f"Cannot specify multiple layout sources ({', '.join(provided)}). Please choose only one layout source."
        )

    # 1. Built-in layout preset key
    if layout_key is not None:
        if layout_key not in BUILTIN_LAYOUT_PRESETS:
            avail = ", ".join(BUILTIN_LAYOUT_PRESETS.keys())
            raise ValueError(
                f"Unknown layout preset key '{layout_key}'. Available presets: {avail}"
            )
        preset = BUILTIN_LAYOUT_PRESETS[layout_key]
        return preset["dsl_template"], f"builtin_preset:{layout_key}"

    # 2. Live source slide ID
    if source_slide_id is not None:
        try:
            res = client.get(SLIDE_ATTRIBUTES_PATH, params={"slideIds": str(source_slide_id)})
            dsl_text = ""
            if isinstance(res, list) and res:
                for item in res:
                    if str(item.get("slideId")) == str(source_slide_id) or len(res) == 1:
                        attrs = item.get("attributes")
                        if isinstance(attrs, str):
                            dsl_text = attrs
                            break
                        elif isinstance(attrs, dict) and "dsl" in attrs:
                            dsl_text = str(attrs["dsl"])
                            break
            elif isinstance(res, dict):
                attrs = res.get("attributes", {})
                dsl_text = attrs if isinstance(attrs, str) else str(attrs.get("dsl", ""))
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch v2 DSL attributes for source slide '{source_slide_id}': {e}"
            ) from e

        if not dsl_text or not dsl_text.strip():
            raise ValueError(
                f"No valid v2 DSL attribute content found on source slide ID '{source_slide_id}'."
            )
        return dsl_text, f"source_slide:{source_slide_id}"

    # 3. Template ID from public templates
    if template_id is not None:
        dsl_text = ""
        # Search public templates catalog
        try:
            pub_res = client.get(PUBLIC_TEMPLATES_PATH)
            if isinstance(pub_res, list):
                for item in pub_res:
                    if str(item.get("id")) == str(template_id):
                        attrs = item.get("attributes")
                        if isinstance(attrs, dict) and "dsl" in attrs:
                            dsl_text = str(attrs["dsl"])
                        elif isinstance(attrs, str):
                            dsl_text = attrs
                        elif "dsl" in item:
                            dsl_text = str(item["dsl"])
                        break
        except Exception:  # noqa: BLE001
            pass

        if not dsl_text:
            # Fallback to slide attributes query
            try:
                res = client.get(SLIDE_ATTRIBUTES_PATH, params={"slideIds": str(template_id)})
                if isinstance(res, list) and res:
                    attrs = res[0].get("attributes")
                    if isinstance(attrs, str):
                        dsl_text = attrs
                    elif isinstance(attrs, dict) and "dsl" in attrs:
                        dsl_text = str(attrs["dsl"])
            except Exception:  # noqa: BLE001
                pass

        if not dsl_text and template_id in BUILTIN_LAYOUT_PRESETS:
            dsl_text = BUILTIN_LAYOUT_PRESETS[template_id]["dsl_template"]

        if not dsl_text or not dsl_text.strip():
            raise ValueError(
                f"Could not resolve v2 DSL content for template ID '{template_id}'."
            )
        return dsl_text, f"template:{template_id}"

    # 4. Local DSL file
    if dsl_file is not None:
        p = Path(dsl_file)
        if not p.is_file():
            raise FileNotFoundError(f"Layout DSL file not found: '{dsl_file}'")
        content = p.read_text(encoding="utf-8")
        if not content.strip():
            raise ValueError(f"Layout DSL file '{dsl_file}' is empty.")
        return content, f"dsl_file:{dsl_file}"

    raise ValueError("No layout source resolved.")


def scope_element_ids(
    dsl: str,
    prefix: str | None = None,
    keep_orig_ids: bool = False,
    slide_order: int | None = None,
) -> str:
    """Scope element IDs in layout DSL using slide order prefixing or explicit prefix."""
    if keep_orig_ids:
        effective_prefix = ""
    elif prefix is not None:
        effective_prefix = prefix
    elif slide_order is not None:
        effective_prefix = f"s{slide_order}"
    else:
        effective_prefix = "s1"

    if effective_prefix:
        # 1. Substitute {id_xyz} placeholders with effective_prefix + xyz
        def _replace_placeholder_id(match: re.Match) -> str:
            raw_key = match.group(1)
            return f"{effective_prefix}{raw_key}"

        scoped_dsl = re.sub(r"\{id_([a-zA-Z0-9_\-]+)\}", _replace_placeholder_id, dsl)

        # 2. Substitute literal id=xyz attributes with id=effective_prefix + xyz if not already prefixed
        def _replace_literal_id(match: re.Match) -> str:
            orig_id = match.group(1)
            if orig_id.startswith(effective_prefix):
                return f"id={orig_id}"
            return f"id={effective_prefix}{orig_id}"

        scoped_dsl = re.sub(r"\bid=([a-zA-Z0-9_\-]+)", _replace_literal_id, scoped_dsl)
        return scoped_dsl
    else:
        # If keeping orig IDs, resolve {id_xyz} placeholders to raw xyz
        return re.sub(r"\{id_([a-zA-Z0-9_\-]+)\}", r"\1", dsl)


def extract_target_content(
    slide_id: str | int,
    client: AhaApiClient,
) -> dict[str, str]:
    """Extract existing text content items from target slide for content preservation."""
    extracted: dict[str, str] = {}

    try:
        elements = list_slide_elements(slide_id, client=client)
    except Exception:  # noqa: BLE001
        elements = []

    titles = [
        e.get("text", "").strip()
        for e in elements
        if e.get("preset") in ["title", "heading"] and e.get("text", "").strip()
    ]
    captions = [
        e.get("text", "").strip()
        for e in elements
        if e.get("preset") == "caption" and e.get("text", "").strip()
    ]
    bodies = [
        e.get("text", "").strip()
        for e in elements
        if e.get("preset") in ["body", "bullet", "subtitle"] and e.get("text", "").strip()
    ]
    other_texts = [
        e.get("text", "").strip()
        for e in elements
        if e.get("preset") not in ["title", "heading", "caption", "body", "bullet", "subtitle"]
        and e.get("text", "").strip()
    ]

    slide_title = ""
    slide_sub = ""
    try:
        sinfo = read_slide(slide_id, client=client)
        raw_slide = sinfo.get("raw_slide", {})
        slide_title = (
            raw_slide.get("title")
            or raw_slide.get("heading")
            or raw_slide.get("sanitizedTitle")
            or ""
        )
        slide_sub = raw_slide.get("subheading") or raw_slide.get("description") or ""
    except Exception:  # noqa: BLE001
        pass

    extracted["title_text"] = (
        titles[0] if titles else (slide_title if slide_title else "Untitled Slide")
    )
    extracted["caption_text"] = (
        captions[0] if captions else (slide_sub if slide_sub else "Section Overview")
    )
    extracted["body_text"] = (
        "\n".join(bodies)
        if bodies
        else ("\n".join(other_texts) if other_texts else "Slide content body text.")
    )

    all_items = bodies + other_texts
    if len(all_items) >= 1:
        extracted["left_title"] = "Option A"
        extracted["left_content"] = all_items[0]
        extracted["card1_title"] = "Item 1"
        extracted["card1_desc"] = all_items[0]
        extracted["step1_title"] = "Step 1"
        extracted["step1_detail"] = all_items[0]

    if len(all_items) >= 2:
        extracted["right_title"] = "Option B"
        extracted["right_content"] = all_items[1]
        extracted["card2_title"] = "Item 2"
        extracted["card2_desc"] = all_items[1]
        extracted["step2_title"] = "Step 2"
        extracted["step2_detail"] = all_items[1]

    if len(all_items) >= 3:
        extracted["banner_title"] = "Summary Framework"
        extracted["banner_content"] = all_items[2]
        extracted["card3_title"] = "Item 3"
        extracted["card3_desc"] = all_items[2]
        extracted["step3_title"] = "Step 3"
        extracted["step3_detail"] = all_items[2]

    extracted["preferred_channel"] = captions[0] if captions else "Direct Channel"
    return extracted


def apply_content_mapping(
    dsl: str,
    user_mappings: dict[str, str],
    preserved_content: dict[str, str] | None = None,
) -> str:
    """Apply placeholder substitutions from user mappings and preserved slide content."""
    defaults = {
        "title_text": "Slide Title",
        "caption_text": "Caption Text",
        "body_text": "Slide content goes here.",
        "left_title": "Option A",
        "left_content": "Details for Option A",
        "right_title": "Option B",
        "right_content": "Details for Option B",
        "banner_title": "Summary Banner",
        "banner_content": "Summary details and notes.",
        "card1_title": "Feature 1",
        "card1_desc": "Description for feature 1.",
        "card2_title": "Feature 2",
        "card2_desc": "Description for feature 2.",
        "card3_title": "Feature 3",
        "card3_desc": "Description for feature 3.",
        "preferred_channel": "Preferred Channel",
        "step1_title": "Step 1",
        "step1_detail": "Step 1 details.",
        "step2_title": "Step 2",
        "step2_detail": "Step 2 details.",
        "step3_title": "Step 3",
        "step3_detail": "Step 3 details.",
    }

    final_mappings = dict(defaults)
    if preserved_content:
        final_mappings.update(preserved_content)
    if user_mappings:
        final_mappings.update(user_mappings)

    def _replace_val(match: re.Match) -> str:
        key = match.group(1)
        if key in final_mappings:
            return str(final_mappings[key])
        return match.group(0)

    return re.sub(r"\{([a-zA-Z0-9_]+)\}", _replace_val, dsl)


def apply_slide_layout(
    slide_id: str | int,
    layout_key: str | None = None,
    source_slide_id: str | None = None,
    template_id: str | None = None,
    dsl_file: str | None = None,
    map_pairs: dict[str, str] | None = None,
    preserve_content: bool = False,
    prefix: str | None = None,
    keep_orig_ids: bool = False,
    lint: bool = False,
    force: bool = False,
    dry_run: bool = False,
    client: AhaApiClient | None = None,
) -> dict[str, Any]:
    """Apply layout preset or DSL template to a target slide with scoping, mapping, and visual linting."""
    if client is None:
        client = AhaApiClient()

    # 1. Fetch target slide info to determine order & presentation ID
    slide_info = read_slide(slide_id, client=client)
    slide_order = slide_info.get("order")
    presentation_id = slide_info.get("presentation_id")

    # 2. Resolve layout DSL template
    raw_dsl, layout_source = resolve_layout_dsl(
        client=client,
        layout_key=layout_key,
        source_slide_id=source_slide_id,
        template_id=template_id,
        dsl_file=dsl_file,
    )

    # 3. Scope element IDs
    scoped_dsl = scope_element_ids(
        raw_dsl,
        prefix=prefix,
        keep_orig_ids=keep_orig_ids,
        slide_order=slide_order,
    )

    # 4. Extract target content if preserve_content is True
    preserved_content = None
    if preserve_content:
        preserved_content = extract_target_content(slide_id, client=client)

    # 5. Apply content mappings
    final_dsl = apply_content_mapping(
        scoped_dsl,
        user_mappings=map_pairs or {},
        preserved_content=preserved_content,
    )

    prefix_used = (
        "kept_original"
        if keep_orig_ids
        else (prefix if prefix is not None else (f"s{slide_order}" if slide_order else "s1"))
    )

    # 6. Dry Run Check
    if dry_run:
        return {
            "slide_id": slide_id,
            "presentation_id": presentation_id,
            "slide_order": slide_order,
            "layout_source": layout_source,
            "prefix_used": prefix_used,
            "preserve_content": preserve_content,
            "user_mappings": map_pairs or {},
            "dry_run": True,
            "status": "dry_run_success",
            "dsl": final_dsl,
        }

    # 7. Apply mutation via POST /api/v2/slides/{slide_id}/attributes
    update_path = UPDATE_ATTRIBUTES_PATH.format(slide_id=slide_id)
    payload = {"attributeKey": "dsl", "attributeValue": final_dsl}

    try:
        client.post(update_path, json_data=payload)
    except Exception as e:
        raise RuntimeError(
            f"Failed to update v2 DSL attributes for slide ID '{slide_id}': {e}"
        ) from e

    # 8. Post-update Visual Linting
    lint_report = None
    lint_passed = True
    if lint:
        boxes, overlaps, syntax_errors, overflows, contrast_errors = lint_slide(
            str(slide_id), client=client
        )
        lint_passed = not (overlaps or syntax_errors or overflows or contrast_errors)
        lint_report = {
            "elements_count": len(boxes),
            "overlaps": overlaps,
            "syntax_errors": syntax_errors,
            "overflows": overflows,
            "contrast_errors": contrast_errors,
            "passed": lint_passed,
        }

        if not lint_passed and not force:
            raise RuntimeError(
                f"Visual linting failed for slide ID '{slide_id}'! "
                f"Overlaps: {len(overlaps)}, Syntax Errors: {len(syntax_errors)}, "
                f"Overflows: {len(overflows)}, Contrast Errors: {len(contrast_errors)}. "
                "Use --force to override linting failure."
            )

    return {
        "slide_id": slide_id,
        "presentation_id": presentation_id,
        "slide_order": slide_order,
        "layout_source": layout_source,
        "prefix_used": prefix_used,
        "preserve_content": preserve_content,
        "user_mappings": map_pairs or {},
        "dry_run": False,
        "status": "success",
        "lint_passed": lint_passed if lint else None,
        "lint_report": lint_report,
        "dsl": final_dsl,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Apply vendor-independent layout presets or layout DSLs to live slides on AhaSlides."
    )
    parser.add_argument("slide_id", help="ID of the target slide to apply layout to.")

    # Layout Source Resolution
    parser.add_argument(
        "-l",
        "--layout",
        dest="layout_key",
        help="Built-in layout preset key from list_slide_layouts.py (e.g. intro_caption_hero, grid_3cards, split_matrix_2col, process_flow_3step).",
    )
    parser.add_argument(
        "-s",
        "--source-slide",
        dest="source_slide_id",
        help="Live source slide ID to extract layout v2 DSL from.",
    )
    parser.add_argument(
        "-t",
        "--template-id",
        dest="template_id",
        help="Public template ID from AhaSlides public-templates catalog.",
    )
    parser.add_argument(
        "-f",
        "--dsl-file",
        dest="dsl_file",
        help="Local file path containing raw layout v2 DSL.",
    )

    # Content Mapping & Preservation
    parser.add_argument(
        "-m",
        "--map",
        dest="map_args",
        action="append",
        nargs="+",
        metavar="KEY=VALUE",
        help="Placeholder key=value mappings (e.g. -m title_text='My Title' -m body_text='Hello World').",
    )
    parser.add_argument(
        "--preserve-content",
        action="store_true",
        help="Extract existing text from target slide and populate matching layout placeholders.",
    )

    # Element ID Scoping
    parser.add_argument(
        "--prefix",
        default=None,
        help="Explicit element ID prefix (overrides auto-prefixing with slide order, e.g. 's14').",
    )
    parser.add_argument(
        "--keep-orig-ids",
        action="store_true",
        help="Do not auto-prefix element IDs in layout DSL.",
    )

    # Validation, Control & Output Flags
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Run post-update visual linting (overlaps, overflows, syntax leaks, contrast).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force applying layout even if visual linting detects errors/warnings.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform resolution, scoping, and mapping without sending mutation request.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON format.",
    )

    args = parser.parse_args()

    # Parse -m / --map KEY=VALUE arguments
    map_pairs: dict[str, str] = {}
    if args.map_args:
        for group in args.map_args:
            for item in group:
                if "=" in item:
                    k, v = item.split("=", 1)
                    map_pairs[k.strip()] = v.strip()

    client = AhaApiClient()

    try:
        res = apply_slide_layout(
            slide_id=args.slide_id,
            layout_key=args.layout_key,
            source_slide_id=args.source_slide_id,
            template_id=args.template_id,
            dsl_file=args.dsl_file,
            map_pairs=map_pairs,
            preserve_content=args.preserve_content,
            prefix=args.prefix,
            keep_orig_ids=args.keep_orig_ids,
            lint=args.lint,
            force=args.force,
            dry_run=args.dry_run,
            client=client,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error applying slide layout: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(res, indent=2))
        return

    print(f"=== Apply Slide Layout Report (Slide ID: {res['slide_id']}) ===")
    print(f"Status:          {res['status']}")
    print(f"Presentation ID: {res['presentation_id']}")
    print(f"Slide Order:     {res['slide_order']}")
    print(f"Layout Source:   {res['layout_source']}")
    print(f"Prefix Used:     {res['prefix_used']}")
    print(f"Preserve Content:{res['preserve_content']}")
    if res.get("lint_passed") is not None:
        print(f"Visual Linting:  {'✅ PASSED' if res['lint_passed'] else '❌ FAILED'}")

    print("\n--- Resulting v2 DSL ---")
    print(res["dsl"])


if __name__ == "__main__":
    main()
