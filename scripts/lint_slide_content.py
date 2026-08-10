#!/usr/bin/env python3
"""Script to lint and validate vendor-independent slides_content.json specification files.

Usage:
    python3 scripts/lint_slide_content.py <json_path>

Example:
    python3 scripts/lint_slide_content.py artifacts/slide-plans/manual_of_me/slides_content.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Base directory setup
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SPEC_PATH = BASE_DIR / "artifacts/slide-plans/manual_of_me/slides_content.json"

# Forbidden vendor/platform-specific keys (case-insensitive check)
FORBIDDEN_VENDOR_KEYS = {
    "presentationid",
    "presentation_id",
    "slideid",
    "slide_id",
    "dsl",
    "attributekey",
    "attributevalue",
    "attributes",
    "ahaslides",
    "preset",
    "offsetx",
    "offsety",
    "basecolour",
    "textcolour",
    "backgroundimage",
}


def find_vendor_keys(obj: Any, path: str = "$") -> list[tuple[str, str]]:
    """Recursively search object for forbidden platform-specific vendor keys."""
    issues = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}"
            if k.lower() in FORBIDDEN_VENDOR_KEYS:
                issues.append((current_path, k))
            issues.extend(find_vendor_keys(v, current_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            current_path = f"{path}[{idx}]"
            issues.extend(find_vendor_keys(item, current_path))
    return issues


def lint_slides_content(spec_path: Path) -> tuple[bool, list[str]]:
    """Lint and validate a slides_content.json specification file against rules.
    
    Returns:
        (passed: bool, log_messages: List[str])
    """
    logs = []
    errors = []

    if not spec_path.exists():
        return False, [f"❌ File not found: {spec_path}"]

    try:
        raw_content = spec_path.read_text(encoding="utf-8")
        data = json.loads(raw_content)
    except json.JSONDecodeError as e:
        return False, [f"❌ Invalid JSON format in {spec_path}: {e}"]
    except Exception as e:
        return False, [f"❌ Failed to read {spec_path}: {e}"]

    logs.append("=== Slide Specification Linter Report ===")
    logs.append(f"File Path: {spec_path}")

    # 1. JSON Pretty-Print & Formatting Uniformity Check
    expected_content = json.dumps(data, indent=2) + "\n"
    if raw_content != expected_content:
        logs.append(
            "❌ JSON Formatting Uniformity Check: FAIL (Non-standard indentation/formatting; expected 2-space indented JSON with a single trailing newline)"
        )
        fmt_passed = False
    else:
        logs.append("✅ JSON Formatting Uniformity Check: PASS (Standard 2-space indented JSON with trailing newline)")
        fmt_passed = True

    # 2. Structural & Root Schema Check
    if not isinstance(data, dict):
        return False, ["❌ Root JSON element must be an object (dictionary)."]

    meta = data.get("fixture_metadata")
    if not isinstance(meta, dict):
        errors.append("Missing mandatory 'fixture_metadata' object.")
    else:
        req_meta = ["name", "title", "version", "total_slides"]
        for field in req_meta:
            if field not in meta:
                errors.append(f"Missing mandatory metadata field: '{field}'")
            elif field in ("title", "name", "version") and isinstance(meta[field], str):
                if meta[field] != meta[field].strip():
                    errors.append(f"Metadata '{field}' has un-trimmed leading/trailing whitespace.")
                if not meta[field].strip():
                    errors.append(f"Metadata '{field}' cannot be empty.")

    slides = data.get("slides")
    if not isinstance(slides, list) or len(slides) == 0:
        errors.append("Missing or empty 'slides' array.")
    else:
        if isinstance(meta, dict) and "total_slides" in meta:
            if meta["total_slides"] != len(slides):
                errors.append(
                    f"Metadata total_slides mismatch: metadata says {meta['total_slides']}, but found {len(slides)} slides."
                )

    if errors:
        logs.append(f"❌ Schema & Metadata Checks: FAIL ({len(errors)} errors)")
        for err in errors:
            logs.append(f"   • {err}")
        return False, logs
    else:
        logs.append(f"✅ Schema & Metadata Checks: PASS (Fixture: '{meta.get('title')}')")

    # 3. Vendor Independence Verification
    vendor_issues = find_vendor_keys(data)
    if vendor_issues:
        logs.append(f"❌ Vendor Independence Verification: FAIL ({len(vendor_issues)} platform-specific keys found)")
        for path, key in vendor_issues:
            logs.append(f"   • Forbidden vendor key '{key}' found at {path}")
        return False, logs
    else:
        logs.append("✅ Vendor Independence Verification: PASS (Zero platform-specific internal keys)")

    # 4. Slide Schema, Field Key Order Uniformity, Value Whitespace, & Content Quality
    slide_errors = []
    seen_slide_keys: set[str] = set()
    
    REQUIRED_SLIDE_KEYS = [
        "slide_number",
        "slide_id_key",
        "title",
        "slide_type",
        "required_keywords",
        "key_content",
        "expected_elements_count",
    ]
    ALLOWED_SLIDE_KEYS = set(REQUIRED_SLIDE_KEYS) | {"subtitle"}

    for idx, slide in enumerate(slides):
        slide_prefix = f"Slide #{idx + 1}"
        if not isinstance(slide, dict):
            slide_errors.append(f"{slide_prefix}: Element is not an object.")
            continue

        # Check key structure & order uniformity
        slide_keys = list(slide.keys())
        
        # Check for unknown / extra / irregular keys
        extra_keys = [k for k in slide_keys if k not in ALLOWED_SLIDE_KEYS]
        if extra_keys:
            slide_errors.append(f"{slide_prefix}: Irregular/extra keys found: {extra_keys}")

        # Check missing mandatory keys
        for req_k in REQUIRED_SLIDE_KEYS:
            if req_k not in slide:
                slide_errors.append(f"{slide_prefix}: Missing mandatory field '{req_k}'.")

        # Determine expected key order for this slide
        if "subtitle" in slide:
            expected_key_order = [
                "slide_number",
                "slide_id_key",
                "title",
                "subtitle",
                "slide_type",
                "required_keywords",
                "key_content",
                "expected_elements_count",
            ]
        else:
            expected_key_order = REQUIRED_SLIDE_KEYS

        if slide_keys != expected_key_order:
            slide_errors.append(
                f"{slide_prefix}: Non-uniform field key structure or ordering. Found {slide_keys}, expected {expected_key_order}"
            )

        # Sequential numbering
        s_num = slide.get("slide_number")
        if not isinstance(s_num, int) or s_num != idx + 1:
            slide_errors.append(f"{slide_prefix}: Incorrect slide_number {s_num} (expected {idx + 1}).")

        # Unique slide_id_key and whitespace check
        s_key = slide.get("slide_id_key")
        if not s_key or not isinstance(s_key, str) or not s_key.strip():
            slide_errors.append(f"{slide_prefix}: Invalid or empty 'slide_id_key'.")
        else:
            if s_key != s_key.strip():
                slide_errors.append(f"{slide_prefix}: 'slide_id_key' has un-trimmed leading/trailing whitespace: '{s_key}'.")
            if s_key in seen_slide_keys:
                slide_errors.append(f"{slide_prefix}: Duplicate 'slide_id_key' '{s_key}'.")
            else:
                seen_slide_keys.add(s_key)

        # Title check and whitespace check
        s_title = slide.get("title")
        if not s_title or not isinstance(s_title, str) or not s_title.strip():
            slide_errors.append(f"{slide_prefix}: 'title' must be a non-empty string.")
        elif s_title != s_title.strip():
            slide_errors.append(f"{slide_prefix}: 'title' has un-trimmed leading/trailing whitespace: '{s_title}'.")

        # Optional Subtitle check (type & whitespace check)
        if "subtitle" in slide:
            s_sub = slide.get("subtitle")
            if not isinstance(s_sub, str):
                slide_errors.append(f"{slide_prefix}: 'subtitle' must be a string if present.")
            elif s_sub != s_sub.strip():
                slide_errors.append(f"{slide_prefix}: 'subtitle' has un-trimmed leading/trailing whitespace: '{s_sub}'.")

        # Slide type check and whitespace check
        s_type = slide.get("slide_type")
        if not s_type or not isinstance(s_type, str) or not s_type.strip():
            slide_errors.append(f"{slide_prefix}: 'slide_type' must be a non-empty string.")
        elif s_type != s_type.strip():
            slide_errors.append(f"{slide_prefix}: 'slide_type' has un-trimmed leading/trailing whitespace: '{s_type}'.")

        # Keywords check and whitespace check
        kws = slide.get("required_keywords")
        if not isinstance(kws, list) or len(kws) == 0:
            slide_errors.append(f"{slide_prefix}: 'required_keywords' must be a non-empty list.")
        else:
            for kw_idx, kw in enumerate(kws):
                if not isinstance(kw, str) or not kw.strip():
                    slide_errors.append(f"{slide_prefix}: Keyword at index {kw_idx} is empty or non-string.")
                elif kw != kw.strip():
                    slide_errors.append(f"{slide_prefix}: Keyword '{kw}' at index {kw_idx} has un-trimmed leading/trailing whitespace.")

        # Key content check
        kc = slide.get("key_content")
        if not isinstance(kc, dict) or len(kc) == 0:
            slide_errors.append(f"{slide_prefix}: 'key_content' must be a non-empty object.")

        # Expected elements count bounds check
        bounds = slide.get("expected_elements_count")
        if not isinstance(bounds, dict):
            slide_errors.append(f"{slide_prefix}: 'expected_elements_count' must be an object with 'min' and 'max'.")
        else:
            min_c = bounds.get("min")
            max_c = bounds.get("max")
            if not isinstance(min_c, int) or min_c <= 0:
                slide_errors.append(f"{slide_prefix}: expected_elements_count.min ({min_c}) must be an integer > 0.")
            if not isinstance(max_c, int) or (isinstance(min_c, int) and max_c < min_c):
                slide_errors.append(f"{slide_prefix}: expected_elements_count.max ({max_c}) must be >= min ({min_c}).")

    if slide_errors:
        logs.append(f"❌ Slide Content & Field Validation: FAIL ({len(slide_errors)} errors)")
        for err in slide_errors:
            logs.append(f"   • {err}")
        slide_passed = False
    else:
        logs.append(f"✅ Slide Content & Field Validation: PASS ({len(slides)} slides validated)")
        slide_passed = True

    overall_passed = fmt_passed and slide_passed
    logs.append("=======================================")
    logs.append(f"OVERALL LINT STATUS: {'✅ PASSED' if overall_passed else '❌ FAILED'}")
    logs.append("=======================================")

    return overall_passed, logs


def main():
    parser = argparse.ArgumentParser(
        description="Lint and validate vendor-independent slides_content.json specification file."
    )
    parser.add_argument(
        "json_path",
        nargs="?",
        default=str(DEFAULT_SPEC_PATH),
        help=f"Path to slides_content.json specification file (default: {DEFAULT_SPEC_PATH}).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw lint result in JSON format.",
    )

    args = parser.parse_args()
    spec_path = Path(args.json_path).resolve()

    passed, logs = lint_slides_content(spec_path)

    if args.json:
        result_payload = {
            "file": str(spec_path),
            "passed": passed,
            "logs": logs,
        }
        print(json.dumps(result_payload, indent=2))
    else:
        for line in logs:
            print(line)

    if not passed:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
