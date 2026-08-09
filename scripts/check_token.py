#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

def main():
    base_dir = Path(__file__).resolve().parent.parent
    config_path = base_dir / "configs" / "config.json"

    if not config_path.exists():
        print(f"[ERROR] Config file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    env_var_name = config.get("token_env_var")
    if not env_var_name:
        print("[ERROR] 'token_env_var' key is not configured in config.json", file=sys.stderr)
        sys.exit(1)

    token_val = os.environ.get(env_var_name)

    if token_val:
        print(f"[SUCCESS] Environment variable '{env_var_name}' was successfully retrieved.")
        print(f"Status: SET | Character Length: {len(token_val)}")
    else:
        print(f"[WARNING] Environment variable '{env_var_name}' is NOT set or empty in the current shell environment.")

if __name__ == "__main__":
    main()
