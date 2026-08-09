#!/usr/bin/env python3
"""Script to read and display presentation details and slide content on AhaSlides using the shared API client."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

DETAIL_PATH_TEMPLATE = "/api/presentation/detail/{presentation_id}"
CANVAS_BLOCKS_PATH = "/api/slide/canvas-blocks"


def fetch_presentation_detail(client: AhaApiClient, presentation_id: str) -> Dict[str, Any]:
    """Fetch presentation detail metadata and slides from AhaSlides API."""
    path = DETAIL_PATH_TEMPLATE.format(presentation_id=presentation_id)
    return client.get(path)


def fetch_slide_canvas_blocks(client: AhaApiClient, slide_id: Any) -> Any:
    """Fetch canvas blocks content for a specific slide ID from AhaSlides API."""
    return client.get(CANVAS_BLOCKS_PATH, params={"slideId": slide_id})


def parse_slide_indices(slide_arg: str, total_slides: int) -> List[int]:
    """Parse slide selection string (e.g. '2', '1-3', '1,3,5-7') into a list of 1-based indices."""
    selected_indices: Set[int] = set()
    parts = [p.strip() for p in slide_arg.split(",") if p.strip()]

    for part in parts:
        range_match = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start > end:
                start, end = end, start
            for idx in range(start, end + 1):
                if 1 <= idx <= total_slides:
                    selected_indices.add(idx)
        elif part.isdigit():
            idx = int(part)
            if 1 <= idx <= total_slides:
                selected_indices.add(idx)

    return sorted(list(selected_indices))


def format_canvas_blocks(blocks_data: Any) -> str:
    """Format canvas blocks data into clean readable text."""
    if not blocks_data:
        return "None"

    if isinstance(blocks_data, list):
        blocks = blocks_data
    elif isinstance(blocks_data, dict):
        blocks = blocks_data.get("blocks") or blocks_data.get("canvasBlocks") or blocks_data.get("items")
        if blocks is None:
            if not blocks_data:
                return "None"
            return json.dumps(blocks_data, indent=2, ensure_ascii=False)
    else:
        return str(blocks_data)

    if isinstance(blocks, list):
        if not blocks:
            return "None"
        formatted_lines = []
        for idx, block in enumerate(blocks, start=1):
            if isinstance(block, dict):
                block_type = block.get("type") or block.get("blockType") or "block"
                text = block.get("text") or block.get("content") or block.get("value") or ""
                if text:
                    formatted_lines.append(f"  - [{block_type}] {text}")
                else:
                    formatted_lines.append(f"  - [{block_type}] {json.dumps(block, ensure_ascii=False)}")
            else:
                formatted_lines.append(f"  - {block}")
        return "\n".join(formatted_lines)

    return json.dumps(blocks_data, indent=2, ensure_ascii=False)


def format_slide_options(options: List[Any]) -> List[str]:
    """Format slide options list into readable bullet points."""
    formatted = []
    for idx, opt in enumerate(options, start=1):
        if isinstance(opt, dict):
            text = opt.get("text") or opt.get("title") or opt.get("label") or opt.get("answer") or f"Option {idx}"
            is_correct = opt.get("isCorrect") or opt.get("correct")
            correct_str = " (Correct)" if is_correct else ""
            formatted.append(f"Option {idx}: {text}{correct_str}")
        else:
            formatted.append(f"Option {idx}: {opt}")
    return formatted


def print_markdown_summary(
    detail: Dict[str, Any],
    slides: List[Dict[str, Any]],
    meta_only: bool = False,
    filtered_indices: Optional[List[int]] = None,
) -> None:
    """Print clean formatted Markdown summary for presentation metadata and slides."""
    pres_id = detail.get("id") or detail.get("_id") or detail.get("presentationId") or "N/A"
    title = detail.get("name") or detail.get("title") or "Untitled Presentation"
    access_code = detail.get("accessCode") or detail.get("code") or "N/A"
    created_at = detail.get("createdAt") or "N/A"
    last_edited = detail.get("lastEditedAt") or detail.get("updatedAt") or "N/A"
    language = detail.get("language") or "N/A"
    total_slides = len(detail.get("Slides") or detail.get("slides") or [])
    url = f"https://presenter.ahaslides.com/presentation/{pres_id}" if pres_id != "N/A" else "N/A"

    print("==================================================")
    print(f"# Presentation: {title}")
    print("==================================================")
    print(f"- **ID**: {pres_id}")
    print(f"- **Access Code**: {access_code}")
    print(f"- **Language**: {language}")
    print(f"- **Created At**: {created_at}")
    print(f"- **Last Edited At**: {last_edited}")
    print(f"- **Total Slides**: {total_slides}")
    print(f"- **URL**: {url}")
    print()

    if meta_only:
        return

    if not slides:
        print("No matching slides found.")
        return

    print("## Slide Details")
    print("--------------------------------------------------")

    for slide in slides:
        slide_num = slide.get("_slide_num", "N/A")
        slide_id = slide.get("id") or slide.get("_id") or "N/A"
        slide_type = slide.get("type") or slide.get("slideType") or "N/A"
        heading = slide.get("title") or slide.get("heading") or slide.get("question") or slide.get("sanitizedTitle") or "N/A"
        subheading = slide.get("subheading") or slide.get("description") or slide.get("titleDesc") or "N/A"
        notes = slide.get("notes") or slide.get("presenterNotes") or slide.get("speakerNotes") or "None"

        print(f"\n### Slide #{slide_num} (ID: {slide_id})")
        print(f"- **Type**: {slide_type}")
        print(f"- **Heading / Text**: {heading}")
        if subheading and subheading != "N/A":
            print(f"- **Subheading / Description**: {subheading}")

        raw_options = slide.get("SlideOptions") or slide.get("options") or slide.get("choices") or []
        if raw_options:
            print("- **Options**:")
            formatted_opts = format_slide_options(raw_options)
            for opt_str in formatted_opts:
                print(f"  - {opt_str}")
        else:
            print("- **Options**: None")

        notes_str = str(notes).strip() if notes else "None"
        print(f"- **Presenter Notes**: {notes_str if notes_str else 'None'}")

        canvas_data = slide.get("canvasBlocks")
        print("- **Canvas Blocks**:")
        blocks_formatted = format_canvas_blocks(canvas_data)
        if "\n" in blocks_formatted:
            print(blocks_formatted)
        else:
            print(f"  {blocks_formatted}")


def print_single_slide_markdown(slide_id: Any, canvas_blocks: Any) -> None:
    """Print formatted markdown summary for a standalone slide fetched by slide_id."""
    print("==================================================")
    print(f"# Slide Canvas Content (Slide ID: {slide_id})")
    print("==================================================")
    print("- **Slide ID**: {}".format(slide_id))
    print("- **Canvas Blocks**:")
    blocks_formatted = format_canvas_blocks(canvas_blocks)
    if "\n" in blocks_formatted:
        print(blocks_formatted)
    else:
        print(f"  {blocks_formatted}")


def main():
    parser = argparse.ArgumentParser(
        description="Read and display presentation details and slide content on AhaSlides."
    )
    parser.add_argument(
        "presentation_id",
        nargs="?",
        default=None,
        help="ID of the presentation to read (required unless --slide-id is given)",
    )
    parser.add_argument(
        "-s",
        "--slide",
        type=str,
        default=None,
        help="Filter specific slide(s) by 1-based index or range (e.g. 2, 1-3, 1,3,5)",
    )
    parser.add_argument(
        "--slide-id",
        type=str,
        default=None,
        help="Filter specific slide by direct slide ID",
    )
    parser.add_argument(
        "--meta",
        "--summary",
        dest="meta_only",
        action="store_true",
        help="Show presentation metadata summary only (do not fetch canvas blocks)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    if not args.presentation_id and not args.slide_id:
        parser.error("presentation_id is required unless --slide-id is specified.")

    client = AhaApiClient()

    # Case 1: Standalone --slide-id without presentation_id
    if not args.presentation_id and args.slide_id:
        canvas_data = fetch_slide_canvas_blocks(client, args.slide_id)
        if args.json:
            result = {"slideId": args.slide_id, "canvasBlocks": canvas_data}
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print_single_slide_markdown(args.slide_id, canvas_data)
        return

    # Case 2: Reading presentation with presentation_id
    detail = fetch_presentation_detail(client, args.presentation_id)

    slides_list = detail.get("Slides") or detail.get("slides") or []
    for idx, slide in enumerate(slides_list, start=1):
        slide["_slide_num"] = idx

    # Filter slides if --slide or --slide-id specified
    filtered_slides = list(slides_list)

    if args.slide_id:
        filtered_slides = [
            s for s in filtered_slides if str(s.get("id") or s.get("_id")) == str(args.slide_id)
        ]

    if args.slide:
        indices = parse_slide_indices(args.slide, len(slides_list))
        filtered_slides = [s for s in filtered_slides if s.get("_slide_num") in indices]

    # Fetch canvas blocks for selected slides unless --meta/--summary is active
    if not args.meta_only:
        for slide in filtered_slides:
            slide_id = slide.get("id") or slide.get("_id")
            if slide_id:
                slide["canvasBlocks"] = fetch_slide_canvas_blocks(client, slide_id)

    if args.json:
        if args.meta_only:
            meta_dict = dict(detail)
            meta_dict.pop("Slides", None)
            meta_dict.pop("slides", None)
            print(json.dumps(meta_dict, indent=2, ensure_ascii=False))
        else:
            output_dict = dict(detail)
            output_dict["Slides"] = filtered_slides
            print(json.dumps(output_dict, indent=2, ensure_ascii=False))
    else:
        print_markdown_summary(
            detail=detail,
            slides=filtered_slides,
            meta_only=args.meta_only,
        )


if __name__ == "__main__":
    main()
