#!/usr/bin/env python3
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urlparse, parse_qs

def load_config(config_path: Path) -> dict:
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def is_excluded(url: str, excluded_patterns: List[str]) -> bool:
    url_lower = url.lower()
    for pattern in excluded_patterns:
        if pattern.lower() in url_lower:
            return True
    return False

def sanitize_headers(headers: List[Dict[str, str]]) -> Dict[str, str]:
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

def inspect_request(entry: Dict[str, Any]) -> Dict[str, Any]:
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
            except Exception:
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
    parser = argparse.ArgumentParser(description="Explore request shape from HAR file safely.")
    parser.add_argument("query", help="URL pattern or keyword to search for in HAR requests (e.g. 'slide/create' or 'attributes')")
    parser.add_argument("har_file", nargs="?", help="Path to HAR file")
    parser.add_argument("-n", "--index", type=int, default=1, help="Which match index to display if multiple found (1-based, default: 1)")
    parser.add_argument("--json", action="store_true", help="Output request specification in JSON format")
    parser.add_argument("--include-excluded", action="store_true", help="Do not apply pattern exclusions from config.json")

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    artifacts_dir = base_dir / "artifacts"
    config_path = base_dir / "configs" / "config.json"
    
    har_path = Path(args.har_file) if args.har_file else get_default_har_file(artifacts_dir)
    
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
    matches = []
    
    for idx, entry in enumerate(entries):
        url = entry.get("request", {}).get("url", "")
        if is_excluded(url, excluded_patterns):
            continue
        if args.query.lower() in url.lower():
            matches.append((idx, entry))

    if not matches:
        print(f"No non-excluded requests matching query '{args.query}' found in {har_path.name}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(matches)} matching request(s) for '{args.query}'.", file=sys.stderr)
    
    target_idx = max(0, min(args.index - 1, len(matches) - 1))
    original_idx, selected_entry = matches[target_idx]
    
    spec = inspect_request(selected_entry)

    if args.json:
        print(json.dumps(spec, indent=2))
    else:
        print("\n" + "=" * 60)
        print(f"REQUEST SHAPE (Match {target_idx + 1} of {len(matches)})")
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
