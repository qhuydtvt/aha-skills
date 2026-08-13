from __future__ import annotations
#!/usr/bin/env python3
"""Snapshot and diff tool for AhaSlides presentation state.

Captures presentation structure and slide DSL attributes to a local JSON snapshot,
then diffs against it to show exactly what changed. Useful for reverse-engineering
new element types: take a snapshot, make changes in the UI, run diff.

Usage:
    # 1. Save current state
    python3 scripts/watch_presentation.py <presentation_id> snapshot [-s SLIDE_IDS]

    # 2. Make changes in the AhaSlides UI

    # 3. Show what changed
    python3 scripts/watch_presentation.py <presentation_id> diff [-s SLIDE_IDS]
"""

import argparse
import difflib
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

PRESENTATION_DETAIL_PATH = "/api/presentation/detail/{presentation_id}"
SLIDE_ATTRIBUTES_PATH = "/api/v2/slides/attributes"
SNAPSHOT_DIR = BASE_DIR / ".snapshots"

# ANSI colours
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

SLIDE_PROP_KEYS = ("id", "type", "order", "baseColour", "textColour", "backgroundImage", "visibility")


# ── helpers ───────────────────────────────────────────────────────────────────

def _snapshot_path(presentation_id: str, slide_ids: list[int] | None) -> Path:
    suffix = "_" + "-".join(str(s) for s in sorted(slide_ids)) if slide_ids else ""
    return SNAPSHOT_DIR / f"snapshot_{presentation_id}{suffix}.json"


def _print_diff(label: str, before: str, after: str) -> None:
    diff = list(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="before",
        tofile="after",
        lineterm="",
    ))
    if not diff:
        return
    print(f"\n{BOLD}{CYAN}🔄 {label}{RESET}")
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            print(f"{GREEN}{line}{RESET}", end="")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"{RED}{line}{RESET}", end="")
        else:
            print(line, end="")
    print()


# ── fetchers ──────────────────────────────────────────────────────────────────

def _fetch_slides(presentation_id: str, client: AhaApiClient) -> list[dict[str, Any]]:
    res = client.get(PRESENTATION_DETAIL_PATH.format(presentation_id=presentation_id))
    return res.get("Slides", [])


def _fetch_dsl(slide_id: int | str, client: AhaApiClient) -> str:
    try:
        res = client.get(SLIDE_ATTRIBUTES_PATH, params={"slideIds": str(slide_id)})
        if isinstance(res, list):
            for item in res:
                attrs = item.get("attributes")
                if isinstance(attrs, str):
                    return attrs
                if isinstance(attrs, dict):
                    return attrs.get("dsl", "")
        if isinstance(res, dict):
            attrs = res.get("attributes")
            if isinstance(attrs, str):
                return attrs
            if isinstance(attrs, dict):
                return attrs.get("dsl", "")
    except Exception:  # noqa: BLE001, S110
        pass
    return ""


def _capture_state(
    presentation_id: str,
    slide_ids: list[int] | None,
    client: AhaApiClient,
) -> dict[str, Any]:
    """Fetch and return the full current state as a serialisable dict."""
    all_slides = _fetch_slides(presentation_id, client)
    if slide_ids:
        all_slides = [s for s in all_slides if s.get("id") in slide_ids]

    slides_state = []
    for slide in sorted(all_slides, key=lambda s: s.get("order", 0)):
        sid = slide["id"]
        slides_state.append({
            "props": {k: slide.get(k) for k in SLIDE_PROP_KEYS},
            "dsl": _fetch_dsl(sid, client),
        })

    return {
        "presentation_id": presentation_id,
        "slide_ids_filter": slide_ids,
        "slides": slides_state,
    }


# ── subcommands ───────────────────────────────────────────────────────────────

def cmd_snapshot(presentation_id: str, slide_ids: list[int] | None, client: AhaApiClient) -> None:
    print(f"📸 Capturing snapshot for presentation {presentation_id}...")
    if slide_ids:
        print(f"   Slides: {slide_ids}")
    else:
        print("   Slides: all")

    state = _capture_state(presentation_id, slide_ids, client)

    SNAPSHOT_DIR.mkdir(exist_ok=True)
    path = _snapshot_path(presentation_id, slide_ids)
    path.write_text(json.dumps(state, indent=2))

    slide_count = len(state["slides"])
    print(f"\n{BOLD}{GREEN}✅ Snapshot saved → {path.relative_to(BASE_DIR)}{RESET}")
    print(f"   {slide_count} slide(s) captured.")
    print("\nNow make changes in the AhaSlides UI, then run:")
    filter_flag = f" -s {','.join(str(s) for s in slide_ids)}" if slide_ids else ""
    print(f"   python3 scripts/watch_presentation.py {presentation_id} diff{filter_flag}")


def cmd_diff(presentation_id: str, slide_ids: list[int] | None, client: AhaApiClient) -> None:
    path = _snapshot_path(presentation_id, slide_ids)
    if not path.exists():
        filter_flag = f" -s {','.join(str(s) for s in slide_ids)}" if slide_ids else ""
        print(
            f"{RED}No snapshot found at {path.relative_to(BASE_DIR)}\n"
            f"Run first:  python3 scripts/watch_presentation.py {presentation_id} snapshot{filter_flag}{RESET}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"🔍 Diffing current state against snapshot for presentation {presentation_id}...")
    old_state: dict[str, Any] = json.loads(path.read_text())
    new_state = _capture_state(presentation_id, slide_ids, client)

    old_slides = {s["props"]["id"]: s for s in old_state["slides"]}
    new_slides = {s["props"]["id"]: s for s in new_state["slides"]}

    changes_found = False

    # Detect added / removed slides
    for sid in new_slides:
        if sid not in old_slides:
            changes_found = True
            s = new_slides[sid]["props"]
            print(f"\n{BOLD}{GREEN}✨ New slide detected: id={sid} type={s.get('type')} order={s.get('order')}{RESET}")

    for sid in old_slides:
        if sid not in new_slides:
            changes_found = True
            print(f"\n{BOLD}{RED}🗑  Slide removed: id={sid}{RESET}")

    # Diff each slide present in both
    for sid, old in old_slides.items():
        if sid not in new_slides:
            continue

        new = new_slides[sid]

        props_before = json.dumps(old["props"], indent=2)
        props_after = json.dumps(new["props"], indent=2)
        if props_before != props_after:
            changes_found = True
            _print_diff(f"Slide properties changed — slide {sid}", props_before, props_after)

        dsl_before = old["dsl"]
        dsl_after = new["dsl"]
        if dsl_before != dsl_after:
            changes_found = True
            _print_diff(f"DSL changed — slide {sid}", dsl_before, dsl_after)

    if not changes_found:
        print(f"\n{YELLOW}No changes detected since last snapshot.{RESET}")
    else:
        print(f"\n{BOLD}Done.{RESET} Re-run snapshot to reset baseline:")
        filter_flag = f" -s {','.join(str(s) for s in slide_ids)}" if slide_ids else ""
        print(f"   python3 scripts/watch_presentation.py {presentation_id} snapshot{filter_flag}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Snapshot and diff AhaSlides presentation state.\n\n"
            "Workflow:\n"
            "  1. python3 scripts/watch_presentation.py <id> snapshot   # save current state\n"
            "  2. Make changes in the AhaSlides UI\n"
            "  3. python3 scripts/watch_presentation.py <id> diff        # see what changed\n\n"
            "Useful for reverse-engineering new element types without HAR recording."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("presentation_id", help="AhaSlides presentation ID.")
    parser.add_argument(
        "command",
        choices=["snapshot", "diff"],
        help="'snapshot' saves current state; 'diff' compares against saved snapshot.",
    )
    parser.add_argument(
        "--slides", "-s",
        default=None,
        help="Comma-separated slide IDs to watch (default: all slides).",
    )

    args = parser.parse_args()

    slide_ids: list[int] | None = None
    if args.slides:
        try:
            slide_ids = [int(s.strip()) for s in args.slides.split(",")]
        except ValueError:
            print("Error: --slides must be comma-separated integers.", file=sys.stderr)
            sys.exit(1)

    client = AhaApiClient()

    if args.command == "snapshot":
        cmd_snapshot(str(args.presentation_id), slide_ids, client)
    else:
        cmd_diff(str(args.presentation_id), slide_ids, client)


if __name__ == "__main__":
    main()
