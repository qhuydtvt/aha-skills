import argparse
import sys
from scripts.shared.api import AhaApiClient

def main():
    parser = argparse.ArgumentParser(description="Dump a slide's raw DSL into a .adsl file.")
    parser.add_argument("slide_id", help="ID of the target slide")
    parser.add_argument("-o", "--output", help="Output file path (default: {slide_id}.adsl)")
    args = parser.parse_args()

    client = AhaApiClient()
    res = client.get("/api/v2/slides/attributes", params={"slideIds": str(args.slide_id)})
    if not res or str(args.slide_id) not in res:
        print(f"Error: Could not retrieve attributes for slide {args.slide_id}", file=sys.stderr)
        sys.exit(1)
        
    attrs = res[str(args.slide_id)].get("attributes", {})
    dsl = attrs.get("dsl", "")
    
    if not dsl:
        print(f"Warning: Slide {args.slide_id} has no DSL content.", file=sys.stderr)
        sys.exit(1)
        
    output_path = args.output if args.output else f"{args.slide_id}.adsl"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(dsl)
        
    print(f"Successfully dumped DSL to {output_path}")

if __name__ == "__main__":
    main()
