from __future__ import annotations
#!/usr/bin/env python3
"""Batch or single-file annotation script to bake structured header metadata comments into ADSL files.

Bakes structured header comments at the top of .adsl content:
  # @presentation_id: 9840079
  # @slide_id: 157065856

Usage:
  python3 scripts/annotate_adsl_metadata.py
  python3 scripts/annotate_adsl_metadata.py --dir artifacts/dsl-templates/
  python3 scripts/annotate_adsl_metadata.py --file artifacts/dsl-templates/pricing_table_3tier_9840079_157065856.adsl
  python3 scripts/annotate_adsl_metadata.py --dry-run
  python3 scripts/annotate_adsl_metadata.py --json
"""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.lib.adsl_metadata import (
    embed_adsl_metadata,
    lint_adsl_file,
    parse_adsl_filename,
    parse_adsl_metadata,
)


def annotate_adsl_file(
    file_path: Path,
    pres_id_override: str | int | None = None,
    slide_id_override: str | int | None = None,
    purpose_override: str | None = None,
    category_override: str | None = None,
    description_override: str | None = None,
    keywords_override: str | list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Annotate a single ADSL file with metadata header comments."""
    content = file_path.read_text(encoding="utf-8")

    parsed_fn = parse_adsl_filename(file_path)
    parsed_meta = parse_adsl_metadata(content)

    pres_id = (
        pres_id_override
        or parsed_fn.get("presentation_id")
        or parsed_meta.get("presentation_id")
    )
    slide_id = (
        slide_id_override
        or parsed_fn.get("slide_id")
        or parsed_meta.get("slide_id")
    )
    purpose = (
        purpose_override
        or parsed_meta.get("purpose")
        or parsed_fn.get("purpose")
    )
    category = category_override or parsed_meta.get("category")
    description = description_override or parsed_meta.get("description")
    keywords = keywords_override or parsed_meta.get("keywords")

    new_content = embed_adsl_metadata(
        content,
        presentation_id=pres_id,
        slide_id=slide_id,
        purpose=purpose,
        category=category,
        description=description,
        keywords=keywords,
    )
    changed = new_content != content

    if changed and not dry_run:
        file_path.write_text(new_content, encoding="utf-8")

    if not pres_id and not slide_id and not purpose:
        status = "skipped (no metadata)"
    elif dry_run:
        status = "dry run (changed)" if changed else "dry run (unchanged)"
    elif changed:
        status = "annotated"
    else:
        status = "unchanged"

    return {
        "file": str(file_path),
        "filename": file_path.name,
        "presentation_id": pres_id,
        "slide_id": slide_id,
        "purpose": purpose,
        "category": category,
        "description": description,
        "keywords": keywords,
        "changed": changed,
        "status": status,
        "size_bytes": len(new_content.encode("utf-8")),
    }


def run_linting(files: list[Path], as_json: bool = False) -> None:
    """Run metadata linting on a list of ADSL files."""
    results = []
    passed_count = 0
    failed_count = 0
    total_errors = 0

    for f in files:
        res = lint_adsl_file(f)
        results.append(res)
        if res["valid"]:
            passed_count += 1
        else:
            failed_count += 1
            total_errors += len(res["errors"])

    if as_json:
        print(
            json.dumps(
                {
                    "total_files": len(files),
                    "passed_count": passed_count,
                    "failed_count": failed_count,
                    "total_errors": total_errors,
                    "valid": failed_count == 0,
                    "results": results,
                },
                indent=2,
            )
        )
        sys.exit(0 if failed_count == 0 else 1)

    print("\n=== ADSL Template Metadata Linter ===")
    print(f"Total Files:  {len(files)}")
    print(f"Passed:       {passed_count}")
    print(f"Failed:       {failed_count}")
    print(f"Total Errors: {total_errors}\n")

    if failed_count > 0:
        print("Linting Failures:")
        for r in results:
            if not r["valid"]:
                print(f"  ❌ {r['filename']}:")
                for err in r["errors"]:
                    print(f"     - {err}")
        print()
        sys.exit(1)
    else:
        print("✅ All ADSL templates passed metadata linting cleanly with 0 errors!\n")
        sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="annotate_adsl_metadata",
        description="Embed/bake header metadata comments (# @presentation_id, # @slide_id, # @purpose, # @category, # @description, # @keywords) into .adsl files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dir",
        default="artifacts/dsl-templates",
        help="Directory containing .adsl files (default: artifacts/dsl-templates).",
    )
    parser.add_argument(
        "--file",
        help="Single .adsl file to annotate or lint (overrides --dir).",
    )
    parser.add_argument(
        "-p", "--presentation-id",
        help="Explicit presentation ID override.",
    )
    parser.add_argument(
        "-s", "--slide-id",
        help="Explicit slide ID override.",
    )
    parser.add_argument(
        "--purpose",
        help="Explicit purpose slug override.",
    )
    parser.add_argument(
        "--category",
        help="Explicit category name override.",
    )
    parser.add_argument(
        "--description",
        help="Explicit structural description override.",
    )
    parser.add_argument(
        "--keywords",
        help="Explicit keywords override (comma-separated).",
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="Lint ADSL template metadata without modifying files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without mutating files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )

    args = parser.parse_args()

    files_to_process: list[Path] = []
    if args.file:
        file_path = Path(args.file)
        if not file_path.is_file():
            print(f"[ERROR] File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        files_to_process.append(file_path)
    else:
        dir_path = Path(args.dir)
        if not dir_path.is_dir():
            print(f"[ERROR] Directory not found: {args.dir}", file=sys.stderr)
            sys.exit(1)
        files_to_process = sorted(dir_path.glob("*.adsl"))

    if not files_to_process:
        if args.json:
            print(json.dumps({"processed_count": 0, "results": []}))
        else:
            print("No .adsl files found to process.")
        return

    if args.lint:
        run_linting(files_to_process, as_json=args.json)

    results = []
    annotated_count = 0
    unchanged_count = 0
    skipped_count = 0

    for f in files_to_process:
        res = annotate_adsl_file(
            f,
            pres_id_override=args.presentation_id,
            slide_id_override=args.slide_id,
            purpose_override=args.purpose,
            category_override=args.category,
            description_override=args.description,
            keywords_override=args.keywords,
            dry_run=args.dry_run,
        )
        results.append(res)
        if "annotated" in res["status"] or "changed" in res["status"]:
            annotated_count += 1
        elif "unchanged" in res["status"]:
            unchanged_count += 1
        else:
            skipped_count += 1

    if args.json:
        print(
            json.dumps(
                {
                    "total_files": len(files_to_process),
                    "annotated_count": annotated_count,
                    "unchanged_count": unchanged_count,
                    "skipped_count": skipped_count,
                    "dry_run": args.dry_run,
                    "results": results,
                },
                indent=2,
            )
        )
        return

    mode_str = " (Dry Run)" if args.dry_run else ""
    print(f"\n=== Annotate ADSL Metadata{mode_str} ===")
    print(f"Total Files: {len(files_to_process)}")
    print(f"Annotated:   {annotated_count}")
    print(f"Unchanged:   {unchanged_count}")
    print(f"Skipped:     {skipped_count}\n")

    # Table preview
    col_widths = [40, 10, 10, 22, 18]
    headers = ["Filename", "Pres ID", "Slide ID", "Purpose", "Status"]
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    sep = "  ".join("-" * w for w in col_widths)

    print(fmt.format(*headers))
    print(sep)
    for r in results:
        fname = r["filename"]
        if len(fname) > 40:
            fname = fname[:37] + "..."
        purp = str(r["purpose"] or "-")
        if len(purp) > 22:
            purp = purp[:19] + "..."
        print(
            fmt.format(
                fname,
                str(r["presentation_id"] or "-"),
                str(r["slide_id"] or "-"),
                purp,
                r["status"],
            )
        )
    print()


if __name__ == "__main__":
    main()

