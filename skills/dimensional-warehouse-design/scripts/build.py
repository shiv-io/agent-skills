# /// script
# requires-python = ">=3.10"
# dependencies = ["openpyxl>=3.1", "pillow>=10", "pyyaml>=6"]
# ///
"""Build the warehouse design workbook and diagrams from a spec file.

    uv run build.py path/to/design_spec.yaml --out path/to/output_dir

Writes <prefix>_warehouse_design.xlsx and four <prefix>_*.excalidraw files, renders PNG copies when
excalidraw-cli is available, then checks the workbook: every internal link resolves and every table tab
lists every column of the spec.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import diagrams  # noqa: E402
import spec_io  # noqa: E402
from workbook import WorkbookBuilder  # noqa: E402


def render_pngs(paths, skip):
    if skip:
        return []
    cli = shutil.which("excalidraw-cli")
    cmd = [cli] if cli else (["npx", "--yes", "@swiftlysingh/excalidraw-cli"] if shutil.which("npx") else None)
    if not cmd:
        print("note: excalidraw-cli and npx not found, so no PNG copies. Install with: npm i -g @swiftlysingh/excalidraw-cli")
        return []
    pngs = []
    for p in paths:
        png = p.replace(".excalidraw", ".png")
        res = subprocess.run(cmd + ["convert", p, "--format", "png", "--padding", "40", "-o", png], capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(png):
            pngs.append(png)
        else:
            print(f"warning: could not render {os.path.basename(p)}: {res.stderr.strip()[:200]}")
    return pngs


def check_workbook(path, spec):
    from openpyxl import load_workbook
    wb = load_workbook(path)
    names, problems, links = set(wb.sheetnames), [], 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.hyperlink is not None and c.hyperlink.location:
                    links += 1
                    m = re.match(r"'(.+)'!", c.hyperlink.location)
                    if not m or m.group(1) not in names:
                        problems.append(f"broken link in {ws.title}!{c.coordinate} -> {c.hyperlink.location}")
    for t in spec.tables:
        ws = wb[t["name"]]
        head = next((r for r in range(1, 60) if ws.cell(r, 2).value == "Column"), None)
        got = [ws.cell(r, 2).value for r in range(head + 1, head + 1 + len(t["columns"]))] if head else []
        if got != [c["name"] for c in t["columns"]]:
            problems.append(f"{t['name']}: tab does not list the spec's columns in order")
    return links, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", help="design spec, .yaml or .json")
    ap.add_argument("--out", default=".", help="output directory (default: current directory)")
    ap.add_argument("--no-png", action="store_true", help="skip PNG rendering")
    args = ap.parse_args()

    try:
        spec = spec_io.load(args.spec)
    except spec_io.SpecError as e:
        sys.exit(str(e))
    os.makedirs(args.out, exist_ok=True)
    prefix = spec.project.get("file_prefix") or "warehouse"
    spec.project["file_prefix"] = prefix

    drawings = diagrams.build_all(spec, args.out)
    pngs = render_pngs(drawings, args.no_png)
    xlsx = WorkbookBuilder(spec, args.out, pngs).build(f"{prefix}_warehouse_design.xlsx")
    links, problems = check_workbook(xlsx, spec)

    n, total = spec.core_share()
    print(f"spec: {len(spec.tables)} tables ({len(spec.core)} core facts), {len(spec.questions)} questions; "
          f"core facts are primary for {n}/{total}" + (f" ({n / total:.0%})" if total else ""))
    print(f"wrote {xlsx} ({len(spec.tables) + 8} tabs, {links} internal links)")
    for p in drawings:
        print(f"wrote {p}" + ("  + .png" if p.replace('.excalidraw', '.png') in pngs else ""))
    if problems:
        print("PROBLEMS:\n  " + "\n  ".join(problems))
        sys.exit(1)
    print("checks passed: every internal link resolves and every table tab lists its columns")


if __name__ == "__main__":
    main()
