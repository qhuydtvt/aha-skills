from __future__ import annotations
#!/usr/bin/env python3
"""Script to insert a new element (:::text directive block) into a slide's DSL content on AhaSlides."""

import argparse
import json
import random
import string
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

SLIDE_ATTRIBUTES_PATH = "/api/v2/slides/attributes"
UPDATE_ATTRIBUTES_PATH = "/api/v2/slides/{slide_id}/attributes"
DEFAULT_FRONTMATTER = "---\ncontent-v2: 1280x720\nversion: 1\n---"

PRESET_DEFAULTS: dict[str, dict[str, Any]] = {
    "title": {"at": "center", "width": "80%", "offset_x": 0, "offset_y": -50},
    "body": {"at": "center", "width": "80%", "offset_x": 0, "offset_y": 0},
    "bullet": {"at": "center", "width": "80%", "offset_x": 0, "offset_y": 50},
    "quote": {"at": "center", "width": "70%", "offset_x": 0, "offset_y": 0},
    "tip": {"at": "center", "width": "75%", "offset_x": 0, "offset_y": 20},
    "subtitle": {"at": "center", "width": "80%", "offset_x": 0, "offset_y": -20},
    "heading": {"at": "center", "width": "80%", "offset_x": 0, "offset_y": -30},
    "image": {"at": "center", "width": "50%", "offset_x": 0, "offset_y": -8},
    "video": {"at": "center", "width": "60%"},
    "timer": {"at": "center", "width": 360, "height": 360},
}


def _generate_element_id(length: int = 10) -> str:
    """Generate a random 10-char alphanumeric element ID."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))


def insert_slide_element(
    slide_id: Any,
    text: str = "",
    preset: str | None = "body",
    at: str | None = None,
    width: str | None = None,
    offset_x: Any | None = 0,
    offset_y: Any | None = None,
    color: str | None = None,
    background: str | None = None,
    border_radius: Any | None = None,
    padding: Any | None = None,
    height: Any | None = None,
    duration: int | None = None,
    display: str | None = None,
    done: str | None = None,
    src: str | None = None,
    extra_attrs: str | None = None,
    raw_dsl: str | None = None,
    element_id: str | None = None,
    client: AhaApiClient | None = None,
) -> dict[str, Any]:
    """Insert a new element (:::text, :::image, :::video, or :::timer directive) into the target slide's DSL.

    Args:
        slide_id: Target slide ID.
        text: Text content / body label of the element.
        preset: Preset type ('body', 'title', 'bullet', 'image', 'video', 'timer', etc.).
        at: Position alignment ('center', etc.).
        width: Element width. % string for text/image/video; px integer for timer.
        offset_x: Horizontal offset (camelCase offsetX in DSL).
        offset_y: Vertical offset (camelCase offsetY in DSL).
        color: Font/text color.
        background: Background color/style.
        border_radius: Border radius value.
        padding: Padding value.
        height: Element height in px (timer only).
        duration: Timer duration in seconds (timer only, default 600).
        display: Timer display style e.g. 'ring' (timer only).
        done: Message shown when timer finishes (timer only).
        src: Media URL. Images: local path or URL (auto-uploaded to CDN).
             Videos: YouTube/Vimeo URL used directly (no upload).
        extra_attrs: Additional raw attribute key=value strings.
        raw_dsl: Complete custom raw DSL block to insert (overrides building block).
        element_id: Specific 10-char element ID (auto-generated if None).
        client: Optional AhaApiClient instance.

    Returns:
        Dict[str, Any]: Insertion metadata and API response.
    """
    if client is None:
        client = AhaApiClient()

    is_image = preset == "image" or (src is not None and preset not in ("video",))
    is_video = preset == "video"
    is_timer = preset == "timer"

    # Timer preset defaults
    if is_timer:
        if duration is None:
            duration = 600
        if display is None:
            display = "ring"

    # Image: provide default src and upload to CDN
    if is_image:
        if not src:
            src = "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=800&q=80"
        if not src.startswith("https://assets-cdn.ahaslides.com/") and not src.startswith("https://dpttlcqctc0a1.cloudfront.net/"):
            from scripts.upload_image import upload_image
            upload_res = upload_image(src, client=client)
            src = upload_res.get("location", src)

    # Video: src used directly — no upload, no CDN conversion

    # 1. Fetch existing DSL
    existing_dsl = ""
    try:
        res = client.get(SLIDE_ATTRIBUTES_PATH, params={"slideIds": str(slide_id)})
        if isinstance(res, list):
            for item in res:
                if (str(item.get("slideId")) == str(slide_id) or len(res) == 1) and item.get("type") == "dsl":
                    attrs = item.get("attributes")
                    if isinstance(attrs, str):
                        existing_dsl = attrs
                        break
                    elif isinstance(attrs, dict) and "dsl" in attrs:
                        existing_dsl = attrs["dsl"]
                        break
        elif isinstance(res, dict):
            attrs = res.get("attributes")
            if isinstance(attrs, str):
                existing_dsl = attrs
            elif isinstance(attrs, dict):
                existing_dsl = attrs.get("dsl", "")
    except Exception:  # noqa: BLE001
        existing_dsl = ""

    if not existing_dsl or not isinstance(existing_dsl, str) or not existing_dsl.strip():
        existing_dsl = DEFAULT_FRONTMATTER

    # 2. Apply preset defaults if parameters not set
    if preset and preset in PRESET_DEFAULTS:
        defaults = PRESET_DEFAULTS[preset]
        if at is None:
            at = defaults.get("at")
        if width is None:
            width = defaults.get("width")
        if offset_y is None:
            offset_y = defaults.get("offset_y")
        if offset_x is None:
            offset_x = defaults.get("offset_x")

    # 3. Generate element_id if missing
    if not element_id:
        element_id = _generate_element_id(10)

    # 4. Construct directive block
    if raw_dsl:
        new_block = raw_dsl.strip()
    else:
        attr_parts = [f"id={element_id}"]
        if preset and not is_image and not is_video and not is_timer:
            attr_parts.append(f"preset={preset}")
        if at:
            attr_parts.append(f"at={at}")
        if width is not None:
            attr_parts.append(f"width={width}")
        if height is not None:
            attr_parts.append(f"height={height}")
        elif is_timer:
            # Apply timer preset height default
            attr_parts.append(f"height={PRESET_DEFAULTS['timer']['height']}")
        if offset_x is not None:
            attr_parts.append(f"offsetX={offset_x}")
        if offset_y is not None:
            attr_parts.append(f"offsetY={offset_y}")
        # Timer-specific attrs
        if is_timer:
            if duration is not None:
                attr_parts.append(f"duration={duration}")
            if display is not None:
                attr_parts.append(f"display={display}")
            if done is not None:
                v = f'"{done}"' if " " in done else done
                attr_parts.append(f"done={v}")
        if src:
            attr_parts.append(f"src={src}")
            # fit=contain only for images, not video
            if is_image and "fit=" not in (extra_attrs or ""):
                attr_parts.append("fit=contain")
        if color:
            attr_parts.append(f"color={color}")
        if background:
            attr_parts.append(f"background={background}")
        if border_radius is not None:
            attr_parts.append(f"border-radius={border_radius}")
        if padding is not None:
            attr_parts.append(f"padding={padding}")
        if extra_attrs:
            attr_parts.append(extra_attrs.strip())

        if is_image:
            directive_type = "image"
        elif is_video:
            directive_type = "video"
        elif is_timer:
            directive_type = "timer"
        else:
            directive_type = "text"
        header = f":::{directive_type} " + " ".join(attr_parts)
        body = text if text else ""
        new_block = f"{header}\n{body}\n:::".strip() if not body else f"{header}\n{body}\n:::"

    # 5. Append to existing DSL
    clean_dsl = existing_dsl.rstrip()
    updated_dsl = clean_dsl + "\n\n" + new_block + "\n"

    # 6. Post update to slide attributes API
    update_path = UPDATE_ATTRIBUTES_PATH.format(slide_id=slide_id)
    payload = {"attributeKey": "dsl", "attributeValue": updated_dsl}

    try:
        api_res = client.post(update_path, json_data=payload)
    except Exception as e:
        raise RuntimeError(f"Failed to update slide attributes for slide ID '{slide_id}': {e}") from e

    result: dict[str, Any] = {
        "slide_id": slide_id,
        "element_id": element_id,
        "preset": preset,
        "text": text,
        "at": at,
        "width": width,
        "offset_x": offset_x,
        "offset_y": offset_y,
        "color": color,
        "background": background,
        "border_radius": border_radius,
        "padding": padding,
        "raw_dsl": new_block,
        "updated_dsl": updated_dsl,
        "api_response": api_res,
    }

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Insert a new :::text element block into a slide's DSL content."
    )
    parser.add_argument(
        "slide_id",
        nargs="?",
        help="ID of the target slide (required).",
    )
    parser.add_argument(
        "text",
        nargs="?",
        default="",
        help="Text content of the new element.",
    )
    parser.add_argument(
        "-p",
        "--preset",
        default="body",
        help="Element preset type (default: 'body').",
    )
    parser.add_argument(
        "--at",
        default=None,
        help="Element alignment (e.g. 'center').",
    )
    parser.add_argument(
        "-w",
        "--width",
        default=None,
        help="Element width (e.g. '80%%').",
    )
    parser.add_argument(
        "-x",
        "--offset-x",
        dest="offset_x",
        default=0,
        help="Horizontal offset (default: 0).",
    )
    parser.add_argument(
        "-y",
        "--offset-y",
        dest="offset_y",
        default=None,
        help="Vertical offset.",
    )
    parser.add_argument(
        "--color",
        default=None,
        help="Font color.",
    )
    parser.add_argument(
        "--bg",
        "--background",
        dest="background",
        default=None,
        help="Background style/color.",
    )
    parser.add_argument(
        "-r",
        "--radius",
        "--border-radius",
        dest="border_radius",
        default=None,
        help="Border radius.",
    )
    parser.add_argument(
        "--padding",
        default=None,
        help="Padding value.",
    )
    parser.add_argument(
        "--src",
        default=None,
        help="Media URL string. For images: Unsplash URL. For videos: YouTube URL.",
    )
    parser.add_argument(
        "--height",
        default=None,
        help="Element height in px (timer only).",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=None,
        help="Timer duration in seconds (timer only).",
    )
    parser.add_argument(
        "--display",
        default=None,
        help="Timer display style e.g., 'ring' (timer only).",
    )
    parser.add_argument(
        "--done",
        default=None,
        help="Message shown when timer finishes (timer only).",
    )
    parser.add_argument(
        "--extra-attrs",
        default=None,
        help="Extra raw attributes string.",
    )
    parser.add_argument(
        "--raw-dsl",
        default=None,
        help="Complete custom raw DSL directive block to insert.",
    )
    parser.add_argument(
        "--id",
        "--element-id",
        dest="element_id",
        default=None,
        help="Custom 10-char element ID.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON format.",
    )

    args = parser.parse_args()

    if not args.slide_id:
        print("Error: 'slide_id' argument is required.", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    try:
        result = insert_slide_element(
            slide_id=args.slide_id,
            text=args.text,
            preset=args.preset,
            at=args.at,
            width=args.width,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
            color=args.color,
            background=args.background,
            border_radius=args.border_radius,
            padding=args.padding,
            height=args.height,
            duration=args.duration,
            display=args.display,
            done=args.done,
            src=args.src,
            extra_attrs=args.extra_attrs,
            raw_dsl=args.raw_dsl,
            element_id=args.element_id,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error inserting slide element: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("=== Slide Element Inserted Successfully ===")
    print(f"Slide ID:     {result['slide_id']}")
    print(f"Element ID:   {result['element_id']}")
    print(f"Preset:       {result['preset'] or 'N/A'}")
    print(f"Text:         \"{result['text']}\"")
    print(f"Position:     at={result['at']}, width={result['width']}, offset=({result['offset_x']}, {result['offset_y']})")
    if result.get("color"):
        print(f"Color:        {result['color']}")
    if result.get("background"):
        print(f"Background:   {result['background']}")
    print(f"DSL Length:   {len(result['updated_dsl'])} bytes")


if __name__ == "__main__":
    main()
