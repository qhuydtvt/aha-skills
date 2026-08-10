#!/usr/bin/env python3
"""Script to verify live AhaSlides presentation content against a vendor-independent slides_content.json specification file slide-by-slide.

Usage:
    python3 scripts/verify_presentation_content.py <presentation_id> [json_spec_path] [--json]

Example:
    python3 scripts/verify_presentation_content.py 9828288 artifacts/slide-plans/manual_of_me/slides_content.json
"""

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

from scripts.list_slide_elements import list_slide_elements
from scripts.read_presentation import (
    fetch_presentation_detail,
    fetch_slide_v2_attributes,
)
from scripts.shared.api import AhaApiClient

# ANSI Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def extract_leaf_strings(data: Any) -> list[str]:
    """Recursively extract leaf string values from nested dict/list structures."""
    strings = []
    if isinstance(data, str):
        s = data.strip()
        if s:
            strings.append(s)
    elif isinstance(data, dict):
        for v in data.values():
            strings.extend(extract_leaf_strings(v))
    elif isinstance(data, list):
        for item in data:
            strings.extend(extract_leaf_strings(item))
    return strings


def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase and simplifying whitespace."""
    if not text:
        return ""
    # Replace multiple whitespaces/newlines with single space
    return re.sub(r"\s+", " ", text.lower()).strip()


def text_contains_phrase(full_text_norm: str, phrase: str) -> bool:
    """Check if normalized full_text contains phrase or essential keywords of phrase."""
    phrase_norm = normalize_text(phrase)
    if not phrase_norm:
        return True

    # 1. Direct substring match
    if phrase_norm in full_text_norm:
        return True

    # 2. Tokenized match for long phrases or bullet lists
    # Extract words with length > 2
    tokens = [w for w in re.findall(r"\b\w+\b", phrase_norm) if len(w) > 2]
    if not tokens:
        return True

    matched = sum(1 for token in tokens if token in full_text_norm)
    # Require at least 80% of essential keywords to match
    return (matched / len(tokens)) >= 0.8


def extract_live_slide_title(slide_dict: dict[str, Any], elements: list[dict[str, Any]], dsl_text: str) -> str:
    """Extract slide title from elements, DSL text, or slide metadata."""
    # 1. Check title element preset
    for elem in elements:
        if elem.get("preset") == "title" and elem.get("text"):
            return elem["text"].strip()

    # 2. Check regex in DSL text
    if dsl_text:
        title_match = re.search(r":::text[^\n]*preset=title[^\n]*\n([^\n]+)", dsl_text)
        if title_match:
            return title_match.group(1).strip()

    # 3. Check slide object fields
    for field in ("title", "heading", "sanitizedTitle", "question"):
        val = slide_dict.get(field)
        if val and isinstance(val, str) and val.strip() and val.strip() != "N/A":
            return val.strip()

    return ""


def extract_full_slide_text(slide_dict: dict[str, Any], elements: list[dict[str, Any]], dsl_text: str) -> str:
    """Extract and combine all text content from a live slide."""
    text_parts = []

    # Metadata fields
    for field in ("title", "subheading", "description", "heading", "titleDesc"):
        val = slide_dict.get(field)
        if val and isinstance(val, str) and val.strip() and val.strip() != "N/A":
            text_parts.append(val.strip())

    # Elements text
    for elem in elements:
        t = elem.get("text")
        if t and isinstance(t, str) and t.strip():
            text_parts.append(t.strip())

    # DSL text full fallback
    if dsl_text:
        text_parts.append(dsl_text)

    return "\n".join(text_parts)


def verify_presentation_content(
    presentation_id: str,
    spec_path: Path,
    client: AhaApiClient | None = None,
) -> dict[str, Any]:
    """Verify live presentation content against vendor-independent JSON spec slide-by-slide."""
    if client is None:
        client = AhaApiClient()

    # Load JSON Spec
    if not spec_path.exists():
        raise FileNotFoundError(f"Specification file not found: {spec_path}")

    with open(spec_path, "r", encoding="utf-8") as f:
        spec_data = json.load(f)

    fixture_meta = spec_data.get("fixture_metadata", {})
    expected_slides_spec = spec_data.get("slides", [])
    expected_total_slides = fixture_meta.get("total_slides", len(expected_slides_spec))

    # Fetch live presentation detail
    pres_detail = fetch_presentation_detail(client, presentation_id)
    live_slides = pres_detail.get("Slides") or pres_detail.get("slides") or []
    live_total_slides = len(live_slides)

    live_slide_ids = [str(s.get("id") or s.get("_id")) for s in live_slides if (s.get("id") or s.get("_id"))]
    dsl_map = fetch_slide_v2_attributes(client, live_slide_ids)

    total_slides_match = (expected_total_slides == live_total_slides)

    slides_report = []
    overall_pass = total_slides_match

    for idx, spec_slide in enumerate(expected_slides_spec, start=1):
        slide_num = spec_slide.get("slide_number", idx)
        expected_title = spec_slide.get("title", "")
        req_keywords = spec_slide.get("required_keywords", [])
        expected_elem_bounds = spec_slide.get("expected_elements_count", {"min": 0, "max": 999})
        min_elem = expected_elem_bounds.get("min", 0)
        max_elem = expected_elem_bounds.get("max", 999)
        key_content_data = spec_slide.get("key_content", {})

        # Check if corresponding live slide exists
        if idx <= len(live_slides):
            live_slide = live_slides[idx - 1]
            slide_id = str(live_slide.get("id") or live_slide.get("_id"))
            dsl_text = dsl_map.get(slide_id, "")
            if isinstance(dsl_text, dict):
                dsl_text = str(dsl_text.get("dsl", ""))

            # Fetch elements using list_slide_elements
            try:
                elements = list_slide_elements(slide_id, client=client)
            except Exception:
                elements = []

            live_title = extract_live_slide_title(live_slide, elements, dsl_text)
            full_text = extract_full_slide_text(live_slide, elements, dsl_text)
            full_text_norm = normalize_text(full_text)

            # 1. Title Matching
            # Pass if expected title normalized equals or is substring of live title normalized (or vice versa)
            exp_title_norm = normalize_text(expected_title)
            live_title_norm = normalize_text(live_title)
            title_match = (exp_title_norm == live_title_norm) or (exp_title_norm in full_text_norm)

            # 2. Required Keywords Verification
            missing_keywords = []
            for kw in req_keywords:
                if not text_contains_phrase(full_text_norm, kw):
                    missing_keywords.append(kw)
            req_keywords_pass = (len(missing_keywords) == 0)

            # 3. Element Count Boundaries Check
            elem_count = len(elements)
            elem_count_valid = (min_elem <= elem_count <= max_elem)

            # 4. Key Content Completeness Check
            key_phrases = extract_leaf_strings(key_content_data)
            missing_key_content = []
            for kp in key_phrases:
                if not text_contains_phrase(full_text_norm, kp):
                    missing_key_content.append(kp)
            key_content_pass = (len(missing_key_content) == 0)

            slide_pass = title_match and req_keywords_pass and elem_count_valid and key_content_pass

        else:
            slide_id = "N/A"
            live_title = ""
            elements = []
            elem_count = 0
            title_match = False
            missing_keywords = list(req_keywords)
            req_keywords_pass = False
            elem_count_valid = False
            key_phrases = extract_leaf_strings(key_content_data)
            missing_key_content = list(key_phrases)
            key_content_pass = False
            slide_pass = False

        if not slide_pass:
            overall_pass = False

        slides_report.append({
            "slide_number": slide_num,
            "slide_id": slide_id,
            "expected_title": expected_title,
            "live_title": live_title,
            "title_match": title_match,
            "element_count": elem_count,
            "element_count_min": min_elem,
            "element_count_max": max_elem,
            "element_count_valid": elem_count_valid,
            "required_keywords": req_keywords,
            "missing_keywords": missing_keywords,
            "required_keywords_pass": req_keywords_pass,
            "key_content_pass": key_content_pass,
            "missing_key_content": missing_key_content,
            "slide_pass": slide_pass,
        })

    result = {
        "presentation_id": presentation_id,
        "spec_file": str(spec_path),
        "total_slides_expected": expected_total_slides,
        "total_slides_live": live_total_slides,
        "total_slides_match": total_slides_match,
        "passed_slides": sum(1 for s in slides_report if s["slide_pass"]),
        "total_slides": len(expected_slides_spec),
        "overall_pass": overall_pass,
        "slides": slides_report,
    }

    return result


def print_colored_report(report: dict[str, Any]) -> None:
    """Print clean, colorized per-slide verification report."""
    print("=" * 80)
    print(f"{BOLD}{CYAN}📊 Presentation Content Verification Report{RESET}")
    print("=" * 80)
    print(f"{BOLD}Presentation ID :{RESET} {report['presentation_id']}")
    print(f"{BOLD}Spec File       :{RESET} {report['spec_file']}")

    match_str = f"{GREEN}MATCH{RESET}" if report["total_slides_match"] else f"{RED}MISMATCH{RESET}"
    print(
        f"{BOLD}Total Slides    :{RESET} {report['total_slides_expected']} expected / {report['total_slides_live']} live ({match_str})"
    )
    print("-" * 80)

    for s in report["slides"]:
        slide_num = s["slide_number"]
        exp_title = s["expected_title"]
        status_tag = f"{GREEN}[PASS]{RESET}" if s["slide_pass"] else f"{RED}[FAIL]{RESET}"

        print(f"\n{BOLD}Slide #{slide_num}:{RESET} \"{exp_title}\" {status_tag}")

        # Title Match
        t_match_str = f"{GREEN}PASS{RESET}" if s["title_match"] else f"{RED}FAIL{RESET} (Live: '{s['live_title']}')"
        print(f"  - Title Match      : {t_match_str}")

        # Element Count
        e_valid_str = (
            f"{GREEN}PASS{RESET} ({s['element_count']} elements, min: {s['element_count_min']}, max: {s['element_count_max']})"
            if s["element_count_valid"]
            else f"{RED}FAIL{RESET} ({s['element_count']} elements, min: {s['element_count_min']}, max: {s['element_count_max']})"
        )
        print(f"  - Element Count    : {e_valid_str}")

        # Required Keywords
        tot_kw = len(s["required_keywords"])
        matched_kw = tot_kw - len(s["missing_keywords"])
        kw_pass_str = f"{GREEN}PASS{RESET} ({matched_kw}/{tot_kw} matched)" if s["required_keywords_pass"] else f"{RED}FAIL{RESET} ({matched_kw}/{tot_kw} matched)"
        print(f"  - Required Keywords: {kw_pass_str}")
        if s["missing_keywords"]:
            print(f"    {YELLOW}Missing Keywords :{RESET} {s['missing_keywords']}")

        # Key Content Completeness
        kc_pass_str = f"{GREEN}PASS{RESET}" if s["key_content_pass"] else f"{RED}FAIL{RESET} ({len(s['missing_key_content'])} items missing)"
        print(f"  - Key Content      : {kc_pass_str}")
        if s["missing_key_content"]:
            print(f"    {YELLOW}Missing Content  :{RESET} {s['missing_key_content']}")

    print("\n" + "=" * 80)
    passed_cnt = report["passed_slides"]
    total_cnt = report["total_slides"]
    overall_res = f"{GREEN}PASS{RESET} (Exit Code 0)" if report["overall_pass"] else f"{RED}FAIL{RESET} (Exit Code 1)"
    print(f"{BOLD}SUMMARY:{RESET} {passed_cnt}/{total_cnt} slides passed verification.")
    print(f"{BOLD}Overall Result:{RESET} {overall_res}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Verify live AhaSlides presentation content against slides_content.json specification file slide-by-slide."
    )
    parser.add_argument(
        "presentation_id",
        help="Target presentation ID (e.g. 9828288)",
    )
    parser.add_argument(
        "json_spec_path",
        nargs="?",
        default=str(BASE_DIR / "artifacts/slide-plans/manual_of_me/slides_content.json"),
        help="Path to vendor-independent slides_content.json spec file (default: artifacts/slide-plans/manual_of_me/slides_content.json)",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output raw JSON verification summary",
    )

    args = parser.parse_args()
    spec_path = Path(args.json_spec_path).resolve()

    try:
        report = verify_presentation_content(
            presentation_id=args.presentation_id,
            spec_path=spec_path,
        )
    except Exception as e:
        if args.json_output:
            print(json.dumps({"error": str(e), "overall_pass": False}, indent=2))
        else:
            print(f"{RED}Error executing verification: {e}{RESET}", file=sys.stderr)
        sys.exit(1)

    if args.json_output:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_colored_report(report)

    sys.exit(0 if report["overall_pass"] else 1)


if __name__ == "__main__":
    main()
