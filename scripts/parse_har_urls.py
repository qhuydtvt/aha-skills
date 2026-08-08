#!/usr/bin/env python3
import json
import sys
import argparse
from pathlib import Path
from typing import List, Set

def load_config(config_path: Path) -> dict:
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_default_har_file(artifacts_dir: Path) -> Path:
    if not artifacts_dir.exists():
        raise FileNotFoundError(f"Artifacts directory not found at {artifacts_dir}")
    
    har_files = list(artifacts_dir.glob("*.har"))
    if not har_files:
        raise FileNotFoundError(f"No .har files found in {artifacts_dir}")
    
    default_target = artifacts_dir / "presenter.ahaslides.com.har"
    if default_target.exists():
        return default_target
    
    har_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return har_files[0]

def is_excluded(url: str, excluded_patterns: List[str]) -> bool:
    url_lower = url.lower()
    for pattern in excluded_patterns:
        if pattern.lower() in url_lower:
            return True
    return False

def extract_urls(har_path: Path, unique: bool = False, include_method: bool = False, excluded_patterns: List[str] = None):
    if excluded_patterns is None:
        excluded_patterns = []

    with open(har_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    entries = data.get("log", {}).get("entries", [])
    urls = []
    seen: Set[str] = set()

    for entry in entries:
        req = entry.get("request", {})
        url = req.get("url")
        method = req.get("method", "GET")
        if not url:
            continue
        
        if is_excluded(url, excluded_patterns):
            continue
        
        item = f"{method} {url}" if include_method else url
        
        if unique:
            if url not in seen:
                seen.add(url)
                urls.append(item)
        else:
            urls.append(item)
            
    return urls

def main():
    parser = argparse.ArgumentParser(description="Parse URL list from HAR file.")
    parser.add_argument("har_file", nargs="?", help="Path to the .har file (defaults to latest/presenter HAR in artifacts/)")
    parser.add_argument("-u", "--unique", action="store_true", help="Deduplicate URLs preserving order")
    parser.add_argument("-m", "--method", action="store_true", help="Include HTTP method (e.g. GET https://...)")
    parser.add_argument("-o", "--output", type=str, help="Output file path to write URLs")
    parser.add_argument("-c", "--config", type=str, help="Path to JSON config file with excluded_patterns")
    parser.add_argument("--ignore-exclusions", action="store_true", help="Disable pattern exclusions")
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).resolve().parent.parent
    artifacts_dir = base_dir / "artifacts"
    default_config_path = base_dir / "configs" / "parser_config.json"
    
    if args.har_file:
        har_path = Path(args.har_file)
    else:
        try:
            har_path = get_default_har_file(artifacts_dir)
        except FileNotFoundError as e:
            har_path = get_default_har_file(Path.cwd() / "artifacts")

    if not har_path.exists():
        print(f"Error: HAR file not found: {har_path}", file=sys.stderr)
        sys.exit(1)

    excluded_patterns = []
    if not args.ignore_exclusions:
        config_path = Path(args.config) if args.config else default_config_path
        config_data = load_config(config_path)
        excluded_patterns = config_data.get("excluded_patterns", [])
        if excluded_patterns:
            print(f"Loaded {len(excluded_patterns)} exclusion patterns from {config_path.name}", file=sys.stderr)
        
    print(f"Parsing HAR file: {har_path}", file=sys.stderr)
    urls = extract_urls(har_path, unique=args.unique, include_method=args.method, excluded_patterns=excluded_patterns)
    
    output_text = "\n".join(urls)
    
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text + "\n" if output_text else "", encoding="utf-8")
        print(f"Saved {len(urls)} URLs to {out_path}", file=sys.stderr)
    else:
        print(output_text)
        print(f"\n--- Total URLs extracted: {len(urls)} ---", file=sys.stderr)

if __name__ == "__main__":
    main()
