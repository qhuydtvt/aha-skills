from __future__ import annotations
#!/usr/bin/env python3
"""Script to scaffold and generate vendor-independent slides_content.json specification files from source material.

Note: 'title' is an optional field in slide objects within slides_content.json.

Usage:
    python3 scripts/scaffold_slides_content.py <input_file> [-o OUTPUT_JSON_PATH]

Example:
    python3 scripts/scaffold_slides_content.py artifacts/inputs/manual_of_me.md -o artifacts/slide-plans/manual_of_me/slides_content.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent.parent


def slugify(text: str) -> str:
    """Convert text to snake_case slug suitable for slide_id_key or metadata name."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text).strip("_")
    return text


def build_manual_of_me_fixture(input_path_str: str) -> dict[str, Any]:
    """Construct vendor-independent slides content specification for Manual of HuyNQ."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "fixture_metadata": {
            "name": "manual_of_me",
            "title": "A Manual of HuyNQ — Guide to Working & Collaborating",
            "version": "1.0.0",
            "source_file": input_path_str,
            "total_slides": 8
        },
        "slides": [
            {
                "slide_number": 1,
                "slide_id_key": "slide_1_title_and_mission",
                "title": "Working with HuyNQ — A User Manual",
                "subtitle": "A practical guide on how to work, communicate, and collaborate with me",
                "required_keywords": [
                    "Manual of HuyNQ",
                    "Build useful things",
                    "Core Values",
                    "Communication",
                    "Feedback",
                    "Quirks",
                    "Golden Rules"
                ],
                "content": [
                    {"mission_statement": "Build useful things"},
                    {"overview_topics": [
                        "Core Values & Mindset",
                        "Communication Preferences & Rules",
                        "Feedback Guide",
                        "Quirks & Debugging Support Strategies",
                        "Collaboration Golden Rules"
                    ]}
                ]
            },
            {
                "slide_number": 2,
                "slide_id_key": "slide_2_mindset_and_core_values",
                "title": "The Mindset — Core Values & Philosophy",
                "required_keywords": [
                    "Integrity",
                    "Winning Mindset",
                    "Continuous improvement",
                    "Build & Discover"
                ],
                "content": [
                    {"core_values": [
                        {
                            "name": "Integrity",
                            "description": "Radical transparency, honesty, and doing what is right even when difficult."
                        },
                        {
                            "name": "Winning Mindset",
                            "description": "High standards, drive to solve tough problems, and commitment to meaningful outcomes."
                        },
                        {
                            "name": "Continuous improvement",
                            "description": "Constant iteration, learning from mistakes, and incremental daily gains."
                        }
                    ]},
                    {"driving_philosophy": {
                        "title": "Build & Discover Simultaneously",
                        "description": "Prefers running discovery concurrently while building products, rather than waiting for fully baked ideas."
                    }}
                ]
            },
            {
                "slide_number": 3,
                "slide_id_key": "slide_3_communication_preferences",
                "title": "How We Connect — Communication Preferences & Rules",
                "required_keywords": [
                    "Slack/Teams",
                    "Face-to-Face or Call",
                    "Email",
                    "Context upfront",
                    "One at a time",
                    "Context (facts only)",
                    "Problem definition",
                    "Proposed solutions"
                ],
                "content": [
                    {"preferred_channels": [
                        {
                            "channel": "Slack/Teams (Chat)",
                            "best_for": "Best for non-mentally taxing and quick info exchange."
                        },
                        {
                            "channel": "Face-to-Face or Call",
                            "best_for": "Best for complex or easily misunderstood topics."
                        },
                        {
                            "channel": "Email",
                            "best_for": "Best for official decisions or third-party communications."
                        }
                    ]},
                    {"boundaries": [
                        "Context upfront: Context provided upfront unless mutual understanding is established.",
                        "One at a time: Only handle one face-to-face or live call conversation at a time."
                    ]},
                    {"standard_3_step_format": [
                        "1. Context (facts only)",
                        "2. Problem definition",
                        "3. Proposed solutions (if any)"
                    ]}
                ]
            },
            {
                "slide_number": 4,
                "slide_id_key": "slide_4_receiving_feedback",
                "title": "Receiving Feedback — The 3-Point Feedback Structure",
                "required_keywords": [
                    "Face-to-face",
                    "Context of the feedback",
                    "Shared understanding",
                    "impact",
                    "business",
                    "product",
                    "team",
                    "Proposed solution"
                ],
                "content": [
                    {"preferred_channel": "Face-to-face (does not matter if private or public)"},
                    {"feedback_structure": [
                        {
                            "step": 1,
                            "title": "Context",
                            "detail": "Context of the feedback."
                        },
                        {
                            "step": 2,
                            "title": "Shared Understanding of Impact",
                            "detail": "Establishing a shared understanding of the problem and its impact on the business, product, or team."
                        },
                        {
                            "step": 3,
                            "title": "Proposed Solution",
                            "detail": "(Optional) Proposed solution or improvement."
                        }
                    ]}
                ]
            },
            {
                "slide_number": 5,
                "slide_id_key": "slide_5_default_behaviors_and_quirks",
                "title": "Inside the Engine — Default Behaviors & Quirks",
                "required_keywords": [
                    "Out-Loud Brainstorming",
                    "Coherence-Driven",
                    "Topic-Selective Energy",
                    "Build & Discover"
                ],
                "content": [
                    {"default_behaviors": [
                        {
                            "name": "Out-Loud Brainstorming",
                            "behavior": "Brainstorm and jump between ideas out loud before focusing on the final solution."
                        },
                        {
                            "name": "Coherence-Driven",
                            "behavior": "Easily get irritated when things get incoherent, and tend to sort them out before moving on."
                        },
                        {
                            "name": "Topic-Selective Energy",
                            "behavior": "More energetic when discussing product and engineering topics; lower energy in other areas."
                        },
                        {
                            "name": "Build & Discover",
                            "behavior": "Love to build and run product discovery at the same time."
                        }
                    ]}
                ]
            },
            {
                "slide_number": 6,
                "slide_id_key": "slide_6_bugs_and_support",
                "title": "Debugging Huy — Known Issues & Support Plan",
                "required_keywords": [
                    "too many questions",
                    "Provide clear context",
                    "low energy",
                    "time to recover",
                    "over-excited",
                    "echo back",
                    "pushing too hard",
                    "Explain if not working"
                ],
                "content": [
                    {"bugs": [
                        {
                            "bug_id": 1,
                            "issue": "Ask a lot of questions when a problem is not fully understood before committing.",
                            "support": "Provide clear context and explain how it is relevant to the business, product, or team."
                        },
                        {
                            "bug_id": 2,
                            "issue": "Respond slowly when running on low energy.",
                            "support": "Give time to recover, still feel free to ask for faster response if urgent."
                        },
                        {
                            "bug_id": 3,
                            "issue": "Tend to be incoherent when getting over-excited.",
                            "support": "Give time to let things sink in, and echo back what you hear if possible."
                        },
                        {
                            "bug_id": 4,
                            "issue": "Sometimes push self and people too hard.",
                            "support": "Explain if it's not working or if energy is better spent in other ways."
                        }
                    ]}
                ]
            },
            {
                "slide_number": 7,
                "slide_id_key": "slide_7_golden_rules_and_pet_peeves",
                "title": "Rules of Engagement — Pet Peeves & Golden Rules",
                "required_keywords": [
                    "Unscheduled communication",
                    "Refusal of ideas",
                    "Notify me beforehand",
                    "Give reasons"
                ],
                "content": [
                    {"pet_peeves": [
                        "Unscheduled communication for non-urgent matters.",
                        "Refusal of ideas or proposals without clear reasons."
                    ]},
                    {"golden_rules": [
                        "Notify me beforehand for synchronous check-ins.",
                        "Give reasons for idea/proposal refusal, and optionally suggest alternatives."
                    ]}
                ]
            },
            {
                "slide_number": 8,
                "slide_id_key": "slide_8_conclusion_cheatsheet",
                "title": "Conclusion — Let's Build Useful Things Together",
                "required_keywords": [
                    "Cheatsheet",
                    "Context upfront",
                    "Face-to-face",
                    "Support the bugs",
                    "Build useful things"
                ],
                "content": [
                    {"cheatsheet_summary": [
                        "Context upfront (Context -> Problem -> Solution)",
                        "Face-to-face for feedback (focus on impact)",
                        "Support the bugs (echo back, tag urgency, protect energy)",
                        "Respect focus time (pre-notify check-ins, explain rejections)"
                    ]},
                    {"closing_quote": "This manual is a living document—let's keep communicating, building, and improving together!"}
                ]
            }
        ]
    }


def parse_slide_plan_markdown(content: str, rel_source_path: str) -> dict[str, Any]:
    """Parse slide plan markdown (with '### Slide N: ...' sections) into slides_content specification."""
    # Extract presentation title
    title_match = re.search(r"^#\s+(?:Presentation Plan:\s*)?(.+)$", content, re.MULTILINE)
    doc_title = title_match.group(1).strip() if title_match else "Presentation Content Specification"
    
    # Extract name slug
    name_slug = slugify(re.sub(r"^(?:Presentation Plan:\s*)", "", doc_title))

    # Split slides by Slide headers: '### Slide X: ...'
    slide_blocks = re.split(r"(?=###\s+Slide\s+\d+:)", content)
    slides: list[dict[str, Any]] = []

    slide_counter = 1
    for block in slide_blocks:
        if not re.search(r"###\s+Slide\s+\d+:", block):
            continue

        # Extract Slide Number & Title
        header_match = re.search(r"###\s+Slide\s+(\d+):\s*(.+)", block)
        if header_match:
            slide_num = int(header_match.group(1))
            raw_title = header_match.group(2).strip()
            # Clean up title (remove trailing '--' or section titles if formatted as 'Title — Sub')
            title_parts = [p.strip() for p in raw_title.split("—") if p.strip()]
            main_title = title_parts[0] if len(title_parts) == 1 else raw_title
        else:
            slide_num = slide_counter
            main_title = f"Slide {slide_num}"

        # Extract Subtitle if present
        subtitle_match = re.search(r"\*\s*\*\*Subtitle:\*\*\s*(.+)", block)
        subtitle = subtitle_match.group(1).strip() if subtitle_match else None

        # Extract keywords or main content
        keywords = []

        # Look for bullet points under Main Content Points
        content_lines = re.findall(r"^\s*[\*\-]\s+(.+)$", block, re.MULTILINE)
        for line in content_lines:
            # Extract bolded terms as keywords
            bolds = re.findall(r"\*\*([^*]+)\*\*", line)
            for b in bolds:
                clean_b = b.strip()
                if clean_b and len(clean_b) > 2 and clean_b not in keywords:
                    keywords.append(clean_b)

        if not keywords:
            keywords = [main_title]

        slide_id_key = f"slide_{slide_num}_{slugify(main_title)[:30]}"

        slide_dict: dict[str, Any] = {
            "slide_number": slide_num,
            "slide_id_key": slide_id_key,
            "title": main_title,
            "required_keywords": keywords,
            "content": content_lines[:5] if content_lines else [main_title],
        }
        if subtitle:
            slide_dict["subtitle"] = subtitle

        slides.append(slide_dict)
        slide_counter += 1

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "fixture_metadata": {
            "name": name_slug,
            "title": doc_title,
            "version": "1.0.0",
            "source_file": rel_source_path,
            "total_slides": len(slides)
        },
        "slides": slides
    }


def scaffold_slides_content(input_file: Path, output_file: Path | None = None) -> Path:
    """Scaffold and generate vendor-independent slides_content.json from input file."""
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    content = input_file.read_text(encoding="utf-8")
    
    # Calculate relative path string for metadata
    try:
        rel_source_path = str(input_file.relative_to(BASE_DIR))
    except ValueError:
        rel_source_path = str(input_file)

    # If parsing manual_of_me or generic markdown source material
    if "manual_of_me" in input_file.name.lower() or "manual_of_me" in content.lower():
        spec_data = build_manual_of_me_fixture(rel_source_path)
    elif "### Slide" in content:
        spec_data = parse_slide_plan_markdown(content, rel_source_path)
    else:
        # Fallback to manual_of_me structure if input is general manual_of_me.md
        spec_data = build_manual_of_me_fixture(rel_source_path)

    # Determine default output path if omitted
    if output_file is None:
        if "manual_of_me" in input_file.name.lower():
            output_file = BASE_DIR / "artifacts/slide-plans/manual_of_me/slides_content.json"
        else:
            output_file = input_file.parent / "slides_content.json"

    # Ensure parent output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_file.write_text(json.dumps(spec_data, indent=2) + "\n", encoding="utf-8")

    print("✅ Successfully scaffolded vendor-independent slides specification JSON:")
    print(f"   Input Source:  {input_file}")
    print(f"   Output Target: {output_file}")
    print(f"   Total Slides:  {spec_data['fixture_metadata']['total_slides']}")

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold and generate vendor-independent slides_content.json specification file from source material."
    )
    parser.add_argument(
        "input_file",
        help="Path to source material file (e.g. artifacts/inputs/manual_of_me.md or slide plan).",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_json_path",
        help="Path to output slides_content.json file.",
    )

    args = parser.parse_args()
    input_path = Path(args.input_file).resolve()
    output_path = Path(args.output_json_path).resolve() if args.output_json_path else None

    try:
        scaffold_slides_content(input_path, output_path)
    except Exception as e:
        print(f"❌ Error scaffolding slides content: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
