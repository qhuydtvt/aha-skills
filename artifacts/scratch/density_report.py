import sys
sys.path.insert(0, '.')
from pathlib import Path
from scripts.list_slide_elements import parse_adsl_to_elements
from scripts.shared.lib.content_density import analyze_element_content, MAX_ELEM_LINES, MAX_ELEM_CHARS, MAX_SLIDE_CHARS, MAX_SLIDE_BULLETS

SLIDES = [
    (1,  157202161),
    (2,  157202165),
    (3,  157202167),
    (4,  157202168),
    (5,  157202169),
    (6,  157202174),
    (7,  157202175),
    (8,  157202176),
]

rows = []
for slide_num, sid in SLIDES:
    path = Path(f"artifacts/dsl-dumps/{sid}.adsl")
    if not path.exists():
        rows.append({"n": slide_num, "slide_id": sid, "error": "DSL not found"})
        continue
    elements = parse_adsl_to_elements(path)
    text_elems = [e for e in elements if e.get("type") == "text"]
    total_chars, total_bullets, max_ec, max_el = 0, 0, 0, 0
    for e in text_elems:
        lc, cc, bc = analyze_element_content(e.get("text", ""))
        total_chars += cc
        total_bullets += bc
        max_ec = max(max_ec, cc)
        max_el = max(max_el, lc)
    rows.append({
        "n": slide_num, "slide_id": sid,
        "total_chars": total_chars, "total_bullets": total_bullets,
        "max_elem_chars": max_ec, "max_elem_lines": max_el,
    })

print(f"\n{'#':>2}  {'slide_id':>12}  {'total_chars':>11} (/{MAX_SLIDE_CHARS})  {'total_bullets':>12} (/{MAX_SLIDE_BULLETS})  {'max_elem_chars':>14} (/{MAX_ELEM_CHARS})  {'max_elem_lines':>14} (/{MAX_ELEM_LINES})")
print("-" * 110)
for r in rows:
    if "error" in r:
        print(f"{r['n']:>2}  {r['slide_id']:>12}  ERROR: {r['error']}")
    else:
        print(f"{r['n']:>2}  {r['slide_id']:>12}  {r['total_chars']:>11}          {r['total_bullets']:>12}            {r['max_elem_chars']:>14}            {r['max_elem_lines']:>14}")
