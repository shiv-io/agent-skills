# /// script
# requires-python = ">=3.10"
# dependencies = ["openpyxl>=3.1"]
# ///
"""Summarise a KPI or reporting spreadsheet so an agent can read its metric definitions.

    uv run extract_spreadsheet.py "Team KPIs.xlsx" --out kpi_outline.md

For each tab it prints the row and column labels, and the first formula on each row, because a formula
is the clearest statement of how a metric is calculated today (COUNTIFS over which column, filtered how).

Tabs that look like raw data exports (many rows under one header row) print only their header row and
their source note. Their rows usually hold customer or patient records, which must not be copied into
the agent's context or into any output. Force a tab either way with --raw or --summary.
"""
import argparse
import re
import sys

from openpyxl import load_workbook

MAX_SUMMARY_ROWS = 400
RAW_ROW_THRESHOLD = 300
ID_CELL_THRESHOLD = 20
IDENTIFIER = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"  # uuid
    r"|[^@\s]+@[^@\s]+\.[a-z]{2,}"                                  # email
    r"|\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}"                            # US phone
    r"|\d{7,}",                                                        # long numeric id
    re.I,
)


def _redact(text):
    return IDENTIFIER.sub("<redacted>", text)


def profile(ws):
    """(non-empty rows, cells that look like a record identifier)."""
    rows = ids = 0
    for row in ws.iter_rows(values_only=True):
        vals = [v for v in row if v not in (None, "")]
        if vals:
            rows += 1
        ids += sum(1 for v in vals if isinstance(v, (str, int)) and not isinstance(v, bool) and IDENTIFIER.fullmatch(str(v).strip()))
    return rows, ids


def is_raw(ws, forced_raw, forced_summary):
    if ws.title in forced_summary:
        return False
    if ws.title in forced_raw:
        return True
    rows, ids = profile(ws)
    return rows >= RAW_ROW_THRESHOLD or ids >= ID_CELL_THRESHOLD


def _header_row(ws, scan=12):
    best, best_n = None, 0
    for r, row in enumerate(ws.iter_rows(min_row=1, max_row=scan, values_only=True), 1):
        n = sum(1 for v in row if isinstance(v, str) and v.strip())
        if n > best_n:
            best, best_n = r, n
    return best if best_n >= 3 else None


def describe(path, forced_raw, forced_summary, max_cols):
    wv = load_workbook(path, data_only=True)
    wf = load_workbook(path, data_only=False)
    out = [f"# Outline of {path}", ""]
    out.append("| Tab | Rows | Columns | Read as |")
    out.append("|---|---|---|---|")
    kinds = {}
    for ws in wv.worksheets:
        kinds[ws.title] = "raw data (headers only)" if is_raw(ws, forced_raw, forced_summary) else "summary / model"
        out.append(f"| {ws.title} | {ws.max_row} | {ws.max_column} | {kinds[ws.title]} |")
    for ws in wv.worksheets:
        f = wf[ws.title]
        out += ["", f"## {ws.title}", ""]
        if kinds[ws.title].startswith("raw"):
            for r in range(1, 4):
                notes = [str(v) for v in next(ws.iter_rows(min_row=r, max_row=r, values_only=True)) if isinstance(v, str)][:3]
                if notes:
                    out.append(f"- note row {r}: " + " | ".join(_redact(n[:120]) for n in notes))
            h = _header_row(ws)
            if h is None:
                out.append("- no header row found; open the tab by hand if its columns matter")
                continue
            headers = [str(v) for v in next(ws.iter_rows(min_row=h, max_row=h, values_only=True)) if v is not None]
            out.append(f"- header row {h}: " + ", ".join(headers))
            formulas = []
            for c in range(1, min(ws.max_column, max_cols) + 1):
                v = f.cell(h + 1, c).value
                if isinstance(v, str) and v.startswith("="):
                    formulas.append(f"{f.cell(h + 1, c).column_letter}: {v[:160]}")
            if formulas:
                out.append("- derived columns (first data row formulas): " + "; ".join(formulas))
            continue
        for r in range(1, min(ws.max_row, MAX_SUMMARY_ROWS) + 1):
            labels, first_val, first_formula = [], None, None
            for c in range(1, min(ws.max_column, max_cols) + 1):
                v, fv = ws.cell(r, c).value, f.cell(r, c).value
                is_formula = isinstance(fv, str) and fv.startswith("=")
                if isinstance(v, str) and v.strip() and not is_formula:
                    labels.append(f"{ws.cell(r, c).coordinate}: {_redact(v.strip()[:80])}")
                elif v is not None and first_val is None:
                    first_val = _redact(f"{ws.cell(r, c).coordinate}={v!r}"[:60])
                    if is_formula:
                        first_formula = fv[:240]
            if labels or first_formula:
                line = f"- r{r}: " + " ; ".join(labels[:8])
                if first_val:
                    line += f"  || {first_val}"
                if first_formula:
                    line += f"  || `{first_formula}`"
                out.append(line)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("xlsx")
    ap.add_argument("--out", help="write markdown here instead of stdout")
    ap.add_argument("--raw", action="append", default=[], help="treat this tab as raw data (repeatable)")
    ap.add_argument("--summary", action="append", default=[], help="treat this tab as a summary (repeatable)")
    ap.add_argument("--max-cols", type=int, default=60)
    args = ap.parse_args()
    text = describe(args.xlsx, set(args.raw), set(args.summary), args.max_cols)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text + "\n")


if __name__ == "__main__":
    main()
