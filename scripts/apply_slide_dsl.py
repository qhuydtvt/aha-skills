import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.shared.api import AhaApiClient

def main():
    parser = argparse.ArgumentParser(description="Apply an .adsl file to a slide's DSL attribute.")
    parser.add_argument("slide_id", help="ID of the target slide")
    parser.add_argument("file", help="Path to the .adsl file")
    args = parser.parse_args()
    
    try:
        with open(args.file, "r", encoding="utf-8") as f:
            dsl = f.read()
    except Exception as e:
        print(f"Error reading {args.file}: {e}", file=sys.stderr)
        sys.exit(1)
        
    client = AhaApiClient()
    payload = {"attributeKey": "dsl", "attributeValue": dsl.strip()}
    try:
        client.post(f"/api/v2/slides/{args.slide_id}/attributes", json_data=payload)
        print(f"Successfully applied DSL from {args.file} to slide {args.slide_id}")
    except Exception as e:
        print(f"Error applying DSL: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
