from __future__ import annotations
#!/usr/bin/env python3
"""Script to update an existing element (:::text or :::shape block) in a slide's DSL content on AhaSlides."""

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

from scripts.shared.api import AhaApiClient

SLIDE_ATTRIBUTES_PATH = "/api/v2/slides/attributes"
UPDATE_ATTRIBUTES_PATH = "/api/v2/slides/{slide_id}/attributes"


def update_slide_element(
    slide_id: Any,
    element_id: str,
    text: str | None = None,
    x: Any | None = None,
    y: Any | None = None,
    w: Any | None = None,
    h: Any | None = None,
    at: str | None = None,
    width: str | None = None,
    offset_x: Any | None = None,
    offset_y: Any | None = None,
    color: str | None = None,
    background: str | None = None,
    border_radius: Any | None = None,
    padding: Any | None = None,
    src: str | None = None,
    extra_attrs: str | None = None,
    client: AhaApiClient | None = None,
) -> dict[str, Any]:
    """Find and update an existing directive element (:::text, :::image, :::shape, :::icon) in a slide's DSL.

    Args:
        slide_id: Target slide ID.
        element_id: Target element ID to modify.
        text: New body text content (if None, existing text is retained).
        x: Explicit X coordinate.
        y: Explicit Y coordinate.
        w: Explicit width.
        h: Explicit height.
        at: Relative alignment ('center', etc.).
        width: Relative width ('80%', etc.).
        offset_x: Relative horizontal offset ('offset-x').
        offset_y: Relative vertical offset ('offset-y').
        color: Text color hex/name.
        background: Background style/color.
        border_radius: Border radius value.
        padding: Padding value.
        src: Image URL string.
        extra_attrs: Key=value pairs to add or override.
        client: Optional AhaApiClient instance.

    Returns:
        Dict[str, Any]: Execution summary, changed attributes, updated DSL, and API response.
    """
    if client is None:
        client = AhaApiClient()

    # 1. Query existing slide attributes
    try:
        res = client.get(SLIDE_ATTRIBUTES_PATH, params={"slideIds": str(slide_id)})
    except Exception as e:
        raise RuntimeError(
            f"Failed to fetch slide attributes for slide ID '{slide_id}': {e}"
        ) from e

    dsl_text = ""
    if isinstance(res, list):
        for item in res:
            if str(item.get("slideId")) == str(slide_id) or len(res) == 1:
                attrs = item.get("attributes")
                if isinstance(attrs, str):
                    dsl_text = attrs
                    break
                elif isinstance(attrs, dict) and "dsl" in attrs:
                    dsl_text = str(attrs["dsl"])
                    break
    elif isinstance(res, dict):
        attrs = res.get("attributes")
        if isinstance(attrs, str):
            dsl_text = attrs
        elif isinstance(attrs, dict):
            dsl_text = str(attrs.get("dsl", ""))

    if not dsl_text or not isinstance(dsl_text, str):
        raise ValueError(
            f"No valid DSL content found for slide ID '{slide_id}'."
        )

    # 2. Parse DSL blocks to locate target element
    pattern = re.compile(
        r"(:::(text|shape|image|icon)([^\n]*)\n(.*?)(?:\n:::\s*|\Z))", re.DOTALL
    )
    attr_kv_pattern = re.compile(r'([\w-]+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')

    target_match = None
    target_directive = "text"
    attr_map: dict[str, str] = {}
    existing_text = ""

    for match in pattern.finditer(dsl_text):
        header_attr_str = match.group(3)
        temp_attrs: dict[str, str] = {}
        for attr_match in attr_kv_pattern.finditer(header_attr_str):
            k = attr_match.group(1)
            v = (
                attr_match.group(2)
                or attr_match.group(3)
                or attr_match.group(4)
                or ""
            )
            temp_attrs[k] = v

        if temp_attrs.get("id") == str(element_id):
            target_match = match
            target_directive = match.group(2)
            attr_map = temp_attrs
            existing_text = match.group(4).strip()
            break

    if target_match is None:
        raise ValueError(
            f"Element with ID '{element_id}' not found in slide ID '{slide_id}' DSL."
        )

    # 3. Update header attributes
    if src is not None:
        if not str(src).startswith("https://assets-cdn.ahaslides.com/"):
            from scripts.upload_image import upload_image
            upload_res = upload_image(str(src), client=client)
            src = upload_res.get("location", src)

        attr_map["src"] = str(src)
        if "fit" not in attr_map:
            attr_map["fit"] = "contain"
    if x is not None:
        attr_map["x"] = str(x)
    if y is not None:
        attr_map["y"] = str(y)
    if w is not None:
        attr_map["w"] = str(w)
    if h is not None:
        attr_map["h"] = str(h)
    if at is not None:
        attr_map["at"] = str(at)
    if width is not None:
        attr_map["width"] = str(width)

    if offset_x is not None:
        attr_map["offsetX"] = str(offset_x)
        attr_map.pop("offset-x", None)
    if offset_y is not None:
        attr_map["offsetY"] = str(offset_y)
        attr_map.pop("offset-y", None)
    if color is not None:
        attr_map["color"] = str(color)
    if background is not None:
        attr_map["background"] = str(background)
    if border_radius is not None:
        attr_map["border-radius"] = str(border_radius)
        attr_map.pop("borderRadius", None)
    if padding is not None:
        attr_map["padding"] = str(padding)

    if extra_attrs is not None:
        for attr_match in attr_kv_pattern.finditer(extra_attrs):
            k = attr_match.group(1)
            v = (
                attr_match.group(2)
                or attr_match.group(3)
                or attr_match.group(4)
                or ""
            )
            attr_map[k] = v

    updated_text = text if text is not None else existing_text

    # 4. Reconstruct block & replace in DSL
    header_parts = [f":::{target_directive}"]
    for k, v in attr_map.items():
        if " " in str(v):
            header_parts.append(f'{k}="{v}"')
        else:
            header_parts.append(f"{k}={v}")

    header_line = " ".join(header_parts)
    
    # Ensure there is always a newline after ::: before the next directive block starts
    start_idx, end_idx = target_match.span(1)
    following_text = dsl_text[end_idx:]
    if following_text.startswith(":::"):
        suffix = "\n:::\n"
    else:
        suffix = "\n:::"

    new_block = f"{header_line}\n{updated_text}{suffix}"
    updated_dsl = dsl_text[:start_idx] + new_block + following_text

    # 5. Post updated DSL to API
    update_path = UPDATE_ATTRIBUTES_PATH.format(slide_id=slide_id)
    payload = {"attributeKey": "dsl", "attributeValue": updated_dsl}

    try:
        api_res = client.post(update_path, json_data=payload)
    except Exception as e:
        raise RuntimeError(
            f"Failed to update slide attributes for slide ID '{slide_id}': {e}"
        ) from e

    return {
        "slide_id": slide_id,
        "element_id": element_id,
        "text": updated_text,
        "x": attr_map.get("x"),
        "y": attr_map.get("y"),
        "w": attr_map.get("w"),
        "h": attr_map.get("h"),
        "at": attr_map.get("at"),
        "width": attr_map.get("width"),
        "offset_x": attr_map.get("offset-x") or attr_map.get("offsetX"),
        "offset_y": attr_map.get("offset-y") or attr_map.get("offsetY"),
        "color": attr_map.get("color"),
        "background": attr_map.get("background"),
        "border_radius": attr_map.get("border-radius")
        or attr_map.get("borderRadius"),
        "padding": attr_map.get("padding"),
        "attributes": attr_map,
        "raw_dsl": new_block,
        "updated_dsl": updated_dsl,
        "api_response": api_res,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Update an existing :::text or :::shape element block in a slide's DSL content."
    )
    parser.add_argument(
        "slide_id",
        nargs="?",
        help="ID of the target slide (required).",
    )
    parser.add_argument(
        "element_id",
        nargs="?",
        help="ID of the element to update (required).",
    )
    parser.add_argument(
        "--id",
        "--element-id",
        dest="flag_element_id",
        default=None,
        help="ID of the element to update (alternative to positional element_id).",
    )
    parser.add_argument(
        "-t",
        "--text",
        default=None,
        help="New text content for the element.",
    )
    parser.add_argument(
        "--x",
        default=None,
        help="X coordinate / position attribute.",
    )
    parser.add_argument(
        "--y",
        default=None,
        help="Y coordinate / position attribute.",
    )
    parser.add_argument(
        "--w",
        default=None,
        help="Width (w) attribute.",
    )
    parser.add_argument(
        "--h",
        default=None,
        help="Height (h) attribute.",
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
        help="Element width string (e.g. '80%%').",
    )
    parser.add_argument(
        "-x",
        "--offset-x",
        dest="offset_x",
        default=None,
        help="Horizontal offset.",
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
        help="Image URL string (e.g. Unsplash URL).",
    )
    parser.add_argument(
        "--extra-attrs",
        default=None,
        help="Additional key=value header attributes.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON format.",
    )

    args = parser.parse_args()

    slide_id = args.slide_id
    element_id = args.element_id or args.flag_element_id

    if not slide_id or not element_id:
        print(
            "Error: Both 'slide_id' and 'element_id' arguments are required.",
            file=sys.stderr,
        )
        parser.print_help(sys.stderr)
        sys.exit(1)

    try:
        result = update_slide_element(
            slide_id=slide_id,
            element_id=element_id,
            text=args.text,
            x=args.x,
            y=args.y,
            w=args.w,
            h=args.h,
            at=args.at,
            width=args.width,
            offset_x=args.offset_x,
            offset_y=args.offset_y,
            color=args.color,
            background=args.background,
            border_radius=args.border_radius,
            padding=args.padding,
            src=args.src,
            extra_attrs=args.extra_attrs,
        )
    except Exception as e:  # noqa: BLE001
        print(f"Error updating slide element: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("=== Slide Element Updated Successfully ===")
    print(f"Slide ID:     {result['slide_id']}")
    print(f"Element ID:   {result['element_id']}")
    print(f"Text:         \"{result['text']}\"")
    pos_parts = []
    if result.get("x") is not None:
        pos_parts.append(f"x={result['x']}")
    if result.get("y") is not None:
        pos_parts.append(f"y={result['y']}")
    if result.get("w") is not None:
        pos_parts.append(f"w={result['w']}")
    if result.get("h") is not None:
        pos_parts.append(f"h={result['h']}")
    if result.get("at") is not None:
        pos_parts.append(f"at={result['at']}")
    if result.get("width") is not None:
        pos_parts.append(f"width={result['width']}")
    if (
        result.get("offset_x") is not None
        or result.get("offset_y") is not None
    ):
        pos_parts.append(
            f"offset=({result.get('offset_x')}, {result.get('offset_y')})"
        )
    if pos_parts:
        print(f"Position:     {', '.join(pos_parts)}")
    if result.get("color"):
        print(f"Color:        {result['color']}")
    if result.get("background"):
        print(f"Background:   {result['background']}")
    print(f"DSL Length:   {len(result['updated_dsl'])} bytes")


if __name__ == "__main__":
    main()
