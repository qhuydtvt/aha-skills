#!/usr/bin/env python3
"""Script to create a new presentation on AhaSlides."""

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import requests
from scripts.token_manager import TokenManager

CREATE_ENDPOINT = "https://presenter.ahaslides.com/api/presentation/create/"


def create_presentation(name: str = "My Presentation") -> dict:
    manager = TokenManager()
    token = manager.get_token()
    if not token:
        print("Error: AhaSlides authentication token is not available.", file=sys.stderr)
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
    }
    payload = {
        "name": name,
        "hasDefaultSlide": True,
        "language": "en"
    }

    try:
        response = requests.post(CREATE_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error creating presentation: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            print(f"Response status: {e.response.status_code}", file=sys.stderr)
            print(f"Response body: {e.response.text}", file=sys.stderr)
        sys.exit(1)


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
