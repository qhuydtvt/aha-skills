from __future__ import annotations
#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


def load_config(config_path: Path) -> dict:
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def is_excluded(url: str, excluded_patterns: list[str]) -> bool:
    url_lower = url.lower()
    for pattern in excluded_patterns:
        if pattern.lower() in url_lower:
            return True
    return False

def sanitize_headers(headers: list[dict[str, str]]) -> dict[str, str]:
    sanitized = {}
    for h in headers:
        name = h.get("name", "")
        value = h.get("value", "")
        name_lower = name.lower()

        if name_lower == "authorization":
            if value.lower().startswith("bearer "):
                token_part = value[7:].strip()
                sanitized[name] = f"Bearer <REDACTED_TOKEN_LEN_{len(token_part)}>"
            else:
                sanitized[name] = f"<REDACTED_AUTH_VAL_LEN_{len(value)}>"
        elif any(k in name_lower for k in ["cookie", "token", "secret", "api-key"]):
            sanitized[name] = f"<REDACTED_VAL_LEN_{len(value)}>"
        else:
            sanitized[name] = value
    return sanitized

def get_default_har_file(artifacts_dir: Path) -> Path:
    default_target = artifacts_dir / "presenter.ahaslides.com.har"
    if default_target.exists():
        return default_target
    har_files = list(artifacts_dir.glob("*.har"))
    if not har_files:
        raise FileNotFoundError(f"No .har files found in {artifacts_dir}")
    har_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return har_files[0]

def inspect_request(entry: dict[str, Any]) -> dict[str, Any]:
    req = entry.get("request", {})
    res = entry.get("response", {})
    
    url = req.get("url", "")
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    raw_headers = req.get("headers", [])
    sanitized_hdrs = sanitize_headers(raw_headers)
    
    post_data = req.get("postData", {})
    body_content = None
    body_json = None
    if post_data:
        text = post_data.get("text")
        if text:
            try:
                body_json = json.loads(text)
            except Exception: # noqa: BLE001
                body_content = text
                
    response_info = {
        "status": res.get("status"),
        "statusText": res.get("statusText"),
        "mimeType": res.get("content", {}).get("mimeType", "")
    }
    
    return {
        "method": req.get("method"),
        "url": url,
        "path": parsed_url.path,
        "query_params": query_params,
        "headers": sanitized_hdrs,
        "body_mime_type": post_data.get("mimeType"),
        "body_json": body_json,
        "body_raw": body_content,
        "response": response_info
    }

def main():
    parser = argparse.ArgumentParser(
        description="Explore request shape, parameters, headers, and body payloads from HAR files safely."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Search query: HTTP method (e.g. 'POST'), URL pattern (e.g. 'slide/create'), or 'all'/'*' to match all requests. Defaults to '*'."
    )
    parser.add_argument(
        "har_file",
        nargs="?",
        default=None,
        help="Path to HAR file (defaults to presenter HAR or latest HAR in artifacts/)"
    )
    parser.add_argument(
        "-m", "--method",
        type=str,
        default=None,
        help="Filter requests specifically by HTTP method (case-insensitive, e.g. POST, GET, PUT, PATCH, DELETE)"
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all matching requests sequentially with index numbers, HTTP methods, and URLs"
    )
    parser.add_argument(
        "-n", "--index",
        type=int,
        default=1,
        help="Which match index to display if multiple found (1-based, default: 1)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output request specification in JSON format"
    )
    parser.add_argument(
        "--include-excluded",
        action="store_true",
        help="Do not apply pattern exclusions from config.json"
    )

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    artifacts_dir = base_dir / "artifacts"
    config_path = base_dir / "configs" / "config.json"

    # Smart positional argument resolution
    query_str = "*"
    har_path = None

    if args.query and not args.har_file:
        query_arg = args.query.strip()
        # Check if single positional argument is actually a HAR file path
        if Path(query_arg).exists() or query_arg.endswith(".har"):
            har_path = Path(query_arg)
            query_str = "*"
        else:
            query_str = query_arg
            har_path = get_default_har_file(artifacts_dir)
    elif args.query and args.har_file:
        query_str = args.query.strip()
        har_path = Path(args.har_file)
    elif not args.query and args.har_file:
        query_str = "*"
        har_path = Path(args.har_file)
    else:
        query_str = "*"
        har_path = get_default_har_file(artifacts_dir)

    if not har_path.exists():
        print(f"Error: HAR file not found: {har_path}", file=sys.stderr)
        sys.exit(1)

    excluded_patterns = []
    if not args.include_excluded:
        config_data = load_config(config_path)
        excluded_patterns = config_data.get("excluded_patterns", [])

    with open(har_path, "r", encoding="utf-8") as f:
        har_data = json.load(f)

    entries = har_data.get("log", {}).get("entries", [])
    matches: list[tuple[int, dict[str, Any]]] = []

    is_all_query = query_str in ("", "*") or query_str.lower() == "all"
    method_filter = args.method.strip().lower() if args.method else None

    for idx, entry in enumerate(entries):
        req = entry.get("request", {})
        url = req.get("url", "")
        method = req.get("method", "")

        if not args.include_excluded and is_excluded(url, excluded_patterns):
            continue

        if method_filter and method.lower() != method_filter:
            continue

        if not is_all_query:
            q_lower = query_str.lower()
            method_match = q_lower == method.lower() or q_lower in method.lower()
            url_match = q_lower in url.lower()
            if not (method_match or url_match):
                continue

        matches.append((idx, entry))

    if not matches:
        filter_info = f" with method '{args.method}'" if args.method else ""
        print(f"No non-excluded requests matching query '{query_str}'{filter_info} found in {har_path.name}", file=sys.stderr)
        sys.exit(1)

    if args.list:
        print(f"Found {len(matches)} matching request(s) in {har_path.name}:")
        for i, (orig_idx, entry) in enumerate(matches, 1):
            req_m = entry.get("request", {}).get("method", "")
            req_u = entry.get("request", {}).get("url", "")
            print(f"  [{i:3d}] (HAR entry #{orig_idx + 1:3d}) {req_m:6s} {req_u}")
        return

    target_idx = max(0, min(args.index - 1, len(matches) - 1))
    original_idx, selected_entry = matches[target_idx]

    if len(matches) > 1 and not args.json:
        print(f"Found {len(matches)} matching request(s). Showing match {target_idx + 1} of {len(matches)} (use -n INDEX to select, or -l to list all).", file=sys.stderr)
    elif len(matches) > 1 and args.json:
        print(f"Found {len(matches)} matching request(s). Showing match {target_idx + 1} of {len(matches)}.", file=sys.stderr)

    spec = inspect_request(selected_entry)

    if args.json:
        print(json.dumps(spec, indent=2))
    else:
        print("\n" + "=" * 60)
        print(f"REQUEST SHAPE (Match {target_idx + 1} of {len(matches)}, HAR entry #{original_idx + 1})")
        print("=" * 60)
        print(f"Method:  {spec['method']}")
        print(f"URL:     {spec['url']}")
        print(f"Path:    {spec['path']}")
        
        if spec['query_params']:
            print("\n--- Query Parameters ---")
            for k, v in spec['query_params'].items():
                print(f"  {k}: {v if len(v) > 1 else v[0]}")
                
        print("\n--- Headers (Sanitized) ---")
        for k, v in spec['headers'].items():
            print(f"  {k}: {v}")
            
        if spec['body_json'] is not None:
            print("\n--- Request Body (JSON) ---")
            print(json.dumps(spec['body_json'], indent=2))
        elif spec['body_raw']:
            print(f"\n--- Request Body ({spec['body_mime_type']}) ---")
            print(spec['body_raw'])
            
        print("\n--- Response Info ---")
        print(f"  Status: {spec['response']['status']} {spec['response']['statusText']}")
        print(f"  MimeType: {spec['response']['mimeType']}")
        print("=" * 60)

if __name__ == "__main__":
    main()

