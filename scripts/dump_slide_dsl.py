import argparse
import sys
from pathlib import Path

from scripts.shared.api import AhaApiClient


def main():
    parser = argparse.ArgumentParser(description="Dump a slide's raw DSL into a .adsl file.")
    parser.add_argument("slide_id", help="ID of the target slide")
    parser.add_argument("-o", "--output", help="Output file path (default: artifacts/dsl-dumps/{slide_id}.adsl)")
    args = parser.parse_args()

    client = AhaApiClient()
    res = client.get("/api/v2/slides/attributes", params={"slideIds": str(args.slide_id)})
    dsl = ""
    if isinstance(res, list):
        for item in res:
            if str(item.get("slideId")) == str(args.slide_id) or len(res) == 1:
                attrs = item.get("attributes", {})
                if isinstance(attrs, str):
                    dsl = attrs
                elif isinstance(attrs, dict):
                    dsl = attrs.get("dsl", "")
                break
    elif isinstance(res, dict) and str(args.slide_id) in res:
        attrs = res[str(args.slide_id)].get("attributes", {})
        if isinstance(attrs, str):
            dsl = attrs
        elif isinstance(attrs, dict):
            dsl = attrs.get("dsl", "")
    
    if not dsl:
        print(f"Warning: Slide {args.slide_id} has no DSL content.", file=sys.stderr)
        sys.exit(1)
        
    if not args.output:
        out_file = Path("artifacts/dsl-dumps") / f"{args.slide_id}.adsl"
    else:
        out_file = Path(args.output)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(dsl)
        
    print(f"Successfully dumped DSL to {out_file}")

if __name__ == "__main__":
    main()
