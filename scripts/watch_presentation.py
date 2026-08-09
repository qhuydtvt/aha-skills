#!/usr/bin/env python3
"""Live watcher for AhaSlides presentation state.

Polls presentation structure and slide DSL attributes, printing unified diffs
whenever anything changes. Useful for reverse-engineering new element types:
  1. Run this watcher against a presentation.
  2. Make changes in the AhaSlides UI (insert video, icon, etc.).
  3. Read the diff — exact DSL attribute names are revealed instantly.

Usage:
    python3 scripts/watch_presentation.py <presentation_id> [options]
"""

import argparse
import difflib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

PRESENTATION_DETAIL_PATH = "/api/presentation/detail/{presentation_id}"
SLIDE_ATTRIBUTES_PATH = "/api/v2/slides/attributes"

# ANSI colours
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

SLIDE_PROP_KEYS = ("id", "type", "order", "baseColour", "textColour", "backgroundImage", "visibility")


# ── helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


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
    print(f"\n{BOLD}{CYAN}[{_now()}] 🔄 {label}{RESET}")
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            print(f"{GREEN}{line}{RESET}", end="")
        elif line.startswith("-") and not line.startswith("---"):
            print(f"{RED}{line}{RESET}", end="")
        else:
            print(line, end="")
    print()


def _slide_props_str(slide: dict[str, Any]) -> str:
    return json.dumps({k: slide.get(k) for k in SLIDE_PROP_KEYS}, indent=2)


# ── fetchers ─────────────────────────────────────────────────────────────────

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


# ── watcher ──────────────────────────────────────────────────────────────────

def watch(
    presentation_id: str,
    watch_slide_ids: list[int] | None,
    interval: float,
    client: AhaApiClient,
) -> None:
    print(f"{BOLD}👁  Watching presentation {presentation_id}{RESET}")
    if watch_slide_ids:
        print(f"   Slides: {watch_slide_ids}")
    else:
        print("   Slides: all")
    print(f"   Interval: {interval}s  |  Stop with Ctrl+C\n")

    # ── initial state ──────────────────────────────────────────────────────
    slides = _fetch_slides(presentation_id, client)

    # Filter to requested slides if specified
    if watch_slide_ids:
        slides = [s for s in slides if s.get("id") in watch_slide_ids]

    # slide_id -> props JSON string
    prev_props: dict[int, str] = {s["id"]: _slide_props_str(s) for s in slides}

    # slide_id -> DSL string
    prev_dsls: dict[int, str] = {s["id"]: _fetch_dsl(s["id"], client) for s in slides}

    # ordered slide id list (to detect additions/removals)
    prev_slide_ids: list[int] = [s["id"] for s in slides]

    print(f"{YELLOW}Snapshot taken — {len(slides)} slide(s) loaded. Watching for changes...{RESET}")

    try:
        while True:
            time.sleep(interval)

            # ── fetch fresh state ──────────────────────────────────────────
            try:
                fresh_slides = _fetch_slides(presentation_id, client)
            except Exception as e:  # noqa: BLE001
                print(f"{RED}[{_now()}] ⚠ Fetch error: {e}{RESET}")
                continue

            if watch_slide_ids:
                fresh_slides = [s for s in fresh_slides if s.get("id") in watch_slide_ids]

            fresh_slide_ids = [s["id"] for s in fresh_slides]

            # ── detect new/removed slides ──────────────────────────────────
            added_ids = [sid for sid in fresh_slide_ids if sid not in prev_slide_ids]
            removed_ids = [sid for sid in prev_slide_ids if sid not in fresh_slide_ids]

            for sid in added_ids:
                slide = next((s for s in fresh_slides if s["id"] == sid), {})
                print(f"\n{BOLD}{GREEN}[{_now()}] ✨ New slide detected: id={sid} "
                      f"type={slide.get('type')} order={slide.get('order')}{RESET}")
                prev_props[sid] = _slide_props_str(slide)
                prev_dsls[sid] = _fetch_dsl(sid, client)

            for sid in removed_ids:
                print(f"\n{BOLD}{RED}[{_now()}] 🗑  Slide removed: id={sid}{RESET}")
                prev_props.pop(sid, None)
                prev_dsls.pop(sid, None)

            prev_slide_ids = fresh_slide_ids

            # ── check each slide ───────────────────────────────────────────
            for slide in fresh_slides:
                sid: int = slide["id"]

                # Slide-level properties diff
                new_props = _slide_props_str(slide)
                if new_props != prev_props.get(sid, ""):
                    _print_diff(
                        f"Slide properties changed — slide {sid}",
                        prev_props.get(sid, ""),
                        new_props,
                    )
                    prev_props[sid] = new_props

                # DSL diff
                new_dsl = _fetch_dsl(sid, client)
                if new_dsl != prev_dsls.get(sid, ""):
                    _print_diff(
                        f"DSL changed — slide {sid}",
                        prev_dsls.get(sid, ""),
                        new_dsl,
                    )
                    prev_dsls[sid] = new_dsl

    except KeyboardInterrupt:
        print(f"\n{BOLD}👋 Watching stopped.{RESET}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Live-watch an AhaSlides presentation for DSL and property changes.\n"
            "Make changes in the UI and see exact diffs printed in real-time.\n\n"
            "Useful for reverse-engineering new element types (video, icon, etc.)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("presentation_id", help="AhaSlides presentation ID to watch.")
    parser.add_argument(
        "--slides",
        "-s",
        default=None,
        help="Comma-separated slide IDs to watch (default: all slides).",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=float,
        default=2.0,
        help="Poll interval in seconds (default: 2).",
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
    watch(
        presentation_id=str(args.presentation_id),
        watch_slide_ids=slide_ids,
        interval=args.interval,
        client=client,
    )


if __name__ == "__main__":
    main()
