#!/usr/bin/env python3
"""Script to upload an image file or image URL to AhaSlides CDN using AhaApiClient."""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import requests

from scripts.shared.api import AhaApiClient

UPLOAD_IMAGE_PATH = "https://presenter.ahaslides.com/api/upload/image/"


def upload_image(
    image_source: str,
    access_code: str = "SXGII",
    socket_id: str = "",
    client: AhaApiClient | None = None,
) -> dict[str, Any]:
    """Upload an image file (local path or HTTP URL) to AhaSlides CDN.

    Args:
        image_source: Local file path or HTTP/HTTPS image URL to upload.
        access_code: Presentation access code (e.g. 'SXGII').
        socket_id: Optional socket ID string.
        client: Optional AhaApiClient instance.

    Returns:
        dict[str, Any]: Dictionary containing 'location' (CDN URL), 'key', and API response.
    """
    if client is None:
        client = AhaApiClient()

    token = client.token_manager.get_token()
    if not token:
        print("Error: AhaSlides authentication token is not available.", file=sys.stderr)
        sys.exit(1)

    filename = "upload_image.jpg"
    mime_type = "image/jpeg"
    img_bytes = b""

    if image_source.startswith(("http://", "https://")):
        filename = os.path.basename(image_source.split("?")[0]) or "downloaded_image.jpg"
        if not filename.endswith((".png", ".jpg", ".jpeg", ".webp")):
            filename += ".jpg"
        req = urllib.request.Request(image_source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            img_bytes = resp.read()
    else:
        path = Path(image_source)
        if not path.exists():
            raise FileNotFoundError(f"Local image file not found: {image_source}")
        filename = path.name
        with open(path, "rb") as f:
            img_bytes = f.read()

    if filename.endswith(".png"):
        mime_type = "image/png"
    elif filename.endswith(".webp"):
        mime_type = "image/webp"

    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (filename, img_bytes, mime_type)}
    data = {"accessCode": access_code, "socketId": socket_id, "type": "null"}

    try:
        res = requests.post(UPLOAD_IMAGE_PATH, headers=headers, files=files, data=data)
        res.raise_for_status()
        res_json = res.json()
        file_info = res_json.get("file", {})
        location = file_info.get("location")
        key = file_info.get("key")

        # Invoke resize-images API to generate WebP CDN origin URL
        if location:
            try:
                ext = "png" if filename.endswith(".png") else "jpg"
                resize_res = client.post(
                    "https://presenter.ahaslides.com/api/upload/resize-images/",
                    json_data={"extension": ext, "imageUrl": location},
                )
                if isinstance(resize_res, dict) and "origin" in resize_res:
                    location = resize_res["origin"]
            except Exception as resize_err:  # noqa: BLE001
                print(f"Warning: resize-images step failed, using raw upload URL: {resize_err}", file=sys.stderr)

        return {
            "location": location,
            "key": key,
            "filename": filename,
            "api_response": res_json,
        }
    except requests.exceptions.RequestException as e:
        print(f"Error uploading image to AhaSlides: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            print(f"Status Code: {e.response.status_code}", file=sys.stderr)
            print(f"Response Body: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Upload an image file or URL to AhaSlides CDN."
    )
    parser.add_argument(
        "image_source",
        nargs="?",
        help="Local image file path or HTTP URL to upload.",
    )
    parser.add_argument(
        "-a",
        "--access-code",
        default="SXGII",
        help="Presentation access code (default: 'SXGII').",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in raw JSON format.",
    )

    args = parser.parse_args()

    if not args.image_source:
        print("Error: 'image_source' argument is required.", file=sys.stderr)
        parser.print_help(sys.stderr)
        sys.exit(1)

    try:
        result = upload_image(args.image_source, access_code=args.access_code)
    except Exception as e:  # noqa: BLE001
        print(f"Error uploading image: {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print("=== Image Uploaded Successfully to AhaSlides CDN ===")
    print(f"Filename: {result.get('filename')}")
    print(f"CDN URL:  {result.get('location')}")
    print(f"Key:      {result.get('key')}")


if __name__ == "__main__":
    main()
