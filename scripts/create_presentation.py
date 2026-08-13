from __future__ import annotations
#!/usr/bin/env python3
"""Script to create a new presentation on AhaSlides using the shared API client."""

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

CREATE_PATH = "/api/presentation/create/"


def create_presentation(name: str = "My Presentation") -> dict:
    client = AhaApiClient()
    payload = {
        "name": name,
        "hasDefaultSlide": True,
        "language": "en"
    }
    return client.post(CREATE_PATH, json_data=payload)


def main():
    parser = argparse.ArgumentParser(description="Create a presentation on AhaSlides.")
    parser.add_argument(
        "name",
        nargs="?",
        default="My Presentation",
        help="Name of the presentation (default: 'My Presentation')",
    )
    args = parser.parse_args()

    data = create_presentation(args.name)

    print("=== Presentation Created Successfully ===")
    if isinstance(data, dict):
        pres_id = data.get("id") or data.get("_id") or data.get("presentationId")
        access_code = data.get("accessCode") or data.get("code")
        title = data.get("name") or args.name

        if pres_id:
            print(f"ID: {pres_id}")
        if title:
            print(f"Name: {title}")
        if access_code:
            print(f"Access Code: {access_code}")

        web_url = f"https://presenter.ahaslides.com/presentation/{pres_id}" if pres_id else None
        if web_url:
            print(f"URL: {web_url}")
    else:
        print(data)


if __name__ == "__main__":
    main()
