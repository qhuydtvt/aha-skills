"""Shared AhaSlides API Client."""

import sys
from pathlib import Path
from typing import Any

import requests

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.token_manager import TokenManager

DEFAULT_BASE_URL = "https://presenter.ahaslides.com"


class AhaApiClient:
    """Shared client for executing HTTP requests against AhaSlides APIs using TokenManager."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.token_manager = TokenManager()

    def _get_headers(self) -> dict[str, str]:
        token = self.token_manager.get_token()
        if not token:
            print("Error: AhaSlides authentication token is not available.", file=sys.stderr)
            sys.exit(1)

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "application/json, text/plain, */*",
        }

    def _build_url(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}/{path.lstrip('/')}"

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        url = self._build_url(path)
        headers = self._get_headers()

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_data,
            )
            response.raise_for_status()
            if response.status_code == 204 or not response.content:
                return {}
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Request Error [{method.upper()} {url}]: {e}", file=sys.stderr)
            if hasattr(e, "response") and e.response is not None:
                print(f"Status Code: {e.response.status_code}", file=sys.stderr)
                print(f"Response Body: {e.response.text}", file=sys.stderr)
            sys.exit(1)

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, json_data: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, params=params, json_data=json_data)

    def put(self, path: str, json_data: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
        return self.request("PUT", path, params=params, json_data=json_data)

    def patch(self, path: str, json_data: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> Any:
        return self.request("PATCH", path, params=params, json_data=json_data)

    def delete(self, path: str, params: dict[str, Any] | None = None, json_data: dict[str, Any] | None = None) -> Any:
        return self.request("DELETE", path, params=params, json_data=json_data)
