from __future__ import annotations
#!/usr/bin/env python3
"""Script to scaffold structural vendor-independent slides_content.json specification files.

Generates pure presentation metadata and slide frames from CLI arguments only.
Does not parse or read source file contents.

Usage:
    python3 scripts/scaffold_slides_content.py [-n TOTAL_SLIDES] [-t TITLE] [-s SOURCE_FILE] [-o OUTPUT_JSON_PATH]

Examples:
    python3 scripts/scaffold_slides_content.py -n 6 -t "A Manual of Huy" -s "artifacts/inputs/manual_of_me.md" -o artifacts/slide-plans/manual_of_me/slides_content.json
    python3 scripts/scaffold_slides_content.py -n 5 -t "Product Strategy" -o artifacts/slide-plans/strategy/slides_content.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent


def slugify(text: str) -> str:
    """Convert text to snake_case slug suitable for slide_id_key or metadata name."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text).strip("_")
    return text if text else "presentation"


def scaffold_slides_content(
    total_slides: int = 5,
    title: str = "Untitled Presentation",
    source_file: str = "N/A",
    name_slug: str | None = None,
    output_file: Path | None = None,
) -> Path:
    """Scaffold structural slides_content.json spec with pure metadata and empty content: []."""
    if not name_slug:
        name_slug = slugify(title)

    slides: list[dict[str, Any]] = []
    
    for i in range(1, total_slides + 1):
        if i == 1:
            slide_title = title
            slide_key = f"slide_1_{slugify(title)}"
        else:
            slide_title = f"Topic {i}"
            slide_key = f"slide_{i}_topic_{i}"

        slides.append({
            "slide_number": i,
            "slide_id_key": slide_key,
            "title": slide_title,
            "required_keywords": [slide_title],
            "content": []
        })

    spec_data = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "fixture_metadata": {
            "name": name_slug,
            "title": title,
            "version": "1.0.0",
            "source_file": source_file,
            "total_slides": total_slides,
        },
        "slides": slides,
    }

    if output_file is None:
        output_file = BASE_DIR / "artifacts/slide-plans/slides_content.json"

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(spec_data, indent=2) + "\n", encoding="utf-8")

    print("✅ Successfully scaffolded structural slides specification JSON:")
    print(f"   Title:         {title}")
    print(f"   Total Slides:  {total_slides}")
    print(f"   Source Ref:    {source_file}")
    print(f"   Output Target: {output_file}")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold structural vendor-independent slides_content.json specification file."
    )
    parser.add_argument(
        "source_pos",
        nargs="?",
        default=None,
        help="Optional positional path reference for source file.",
    )
    parser.add_argument(
        "-n",
        "--total-slides",
        type=int,
        default=5,
        dest="total_slides",
        help="Number of slides to scaffold (default: 5).",
    )
    parser.add_argument(
        "-t",
        "--title",
        default="Untitled Presentation",
        dest="title",
        help="Title of the presentation.",
    )
    parser.add_argument(
        "-s",
        "--source-file",
        default=None,
        dest="source_file",
        help="Source file reference path string (stored in metadata).",
    )
    parser.add_argument(
        "--name",
        default=None,
        dest="name",
        help="Fixture name slug.",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_json_path",
        help="Path to output slides_content.json file.",
    )

    args = parser.parse_args()

    # Determine source file string reference
    source_ref = args.source_file or args.source_pos or "N/A"

    output_path = Path(args.output_json_path).resolve() if args.output_json_path else None

    try:
        scaffold_slides_content(
            total_slides=args.total_slides,
            title=args.title,
            source_file=source_ref,
            name_slug=args.name,
            output_file=output_path,
        )
    except Exception as e:
        print(f"❌ Error scaffolding slides content: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
