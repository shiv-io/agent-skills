"""The design workbook: summary, business questions, bus matrix, current models, in-flight work, gaps,
decisions, diagrams, and one tab per table."""
import os

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.hyperlink import Hyperlink

from spec_io import compact_ids, READY, PARTIAL, BLOCKED

FILL = {k: PatternFill("solid", fgColor=v) for k, v in {
    "head": "343A40", "fact": "A5D8FF", "fact_light": "E7F5FF", "dim": "FFEC99", "bridge": "FFF3BF",
    "ok": "B2F2BB", "partial": "FFD8A8", "blocked": "FFC9C9", "pr": "D0BFFF", "new": "FFD8A8",
    "main": "B2F2BB", "rename": "A5D8FF", "grey": "F1F3F5",
}.items()}
THIN = Side(style="thin", color="CED4DA")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LINK = Font(color="1971C2", underline="single")
TITLE = Font(bold=True, size=16)
SUB = Font(italic=True, color="495057")
READY_FILL = {READY: "ok", PARTIAL: "partial", BLOCKED: "blocked"}
STATUS_FILL = {"main": "main", "in_flight": "pr", "new": "new"}
NAV = ["Business questions", "Bus matrix", "Current models", "In-flight work", "Gaps", "Decisions", "Diagrams"]


def _link(cell, tab, text=None):
    cell.value = text or tab
    cell.hyperlink = Hyperlink(ref=cell.coordinate, location=f"'{tab}'!A1")
    cell.font = LINK


def _header(ws, row, labels, widths):
    for i, (label, w) in enumerate(zip(labels, widths), 1):
        c = ws.cell(row=row, column=i, value=label)
        c.font, c.fill, c.alignment, c.border = Font(bold=True, color="FFFFFF"), FILL["head"], CENTER, BORDER
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def _row(ws, row, values, fill=None):
    for i, v in enumerate(values, 1):
        if isinstance(v, (list, tuple)):
            v = ", ".join(map(str, v))
        c = ws.cell(row=row, column=i, value=v)
        c.alignment, c.border = WRAP, BORDER
        if fill:
            c.fill = FILL[fill]


def _title(ws, text, sub=None):
    ws["A1"], ws["A1"].font = text, TITLE
    if sub:
        ws["A2"], ws["A2"].font = sub, SUB
    _link(ws["A3"], "Summary", "← Back to Summary")


def _table_fill(t):
    return {"dimension": "dim", "bridge": "bridge"}.get(t["kind"]) or ("fact" if t["tier"] == "core" else "fact_light")


def _column_status_fill(status):
    s = str(status).lower()
    if s == "exists":
        return "main"
    if s == "rename":
        return "rename"
    if s == "new":
        return "new"
    if s.startswith("gap"):
        return "blocked"
    return "pr"


class WorkbookBuilder:
    def __init__(self, spec, out_dir, diagram_pngs):
        self.spec, self.out_dir, self.pngs = spec, out_dir, diagram_pngs
        self.primary, self.secondary = spec.questions_by_table()
        self.wb = Workbook()

    def summary(self):
        s, ws = self.spec, self.wb.active
        ws.title = "Summary"
        p = s.project
        ws["A1"], ws["A1"].font = f"{p.get('id', '')}: {p.get('title', 'Warehouse design')}".strip(": "), TITLE
        n, total = s.core_share()
        sup = len([t for t in s.facts if t["tier"] != "core" and t["kind"] == "fact"])
        bridges = len([t for t in s.facts if t["kind"] == "bridge"])
        lines = [
            "One row per proposed table. Click a table name to open its tab: grain, primary key, what it is built from, the questions it answers, and every column with type, description and lineage.",
            (f"{len(s.core)} core facts are the primary table for {n} of the {total} business questions ({n / total:.0%}). " if total else "")
            + f"{sup} supporting facts, {bridges} bridge table{'s' if bridges != 1 else ''} and {len(s.dims)} conformed dimensions carry the rest.",
            "Status: 'On main' means a model exists today and is renamed or extended. 'In flight' means the work is on an open pull request or branch. 'New' means no model exists yet.",
            "Readiness: Ready = every column has a source today. Partial = buildable now; some columns stay null until a gap closes. Blocked = the core source is not loaded yet.",
        ]
        if p.get("version") or p.get("date"):
            lines.append(f"Version {p.get('version', '1')}, {p.get('date', '')}. Sources: " + "; ".join(x.get("description", x.get("tag", "")) for x in p.get("sources", [])))
        for i, l in enumerate(lines, 2):
            ws.cell(row=i, column=1, value=l).font = SUB
        ws.cell(row=8, column=1, value="Go to:").font = Font(bold=True)
        for i, tab in enumerate(NAV, 2):
            _link(ws.cell(row=8, column=i), tab)
        r = 10
        _header(ws, r, ["#", "Table", "Kind", "Tier", "Fact type", "Grain", "Primary key", "Status today", "Readiness",
                        "Built from (current models and sources)", "In-flight work", "Primary for questions", "Also used by", "Columns", "New or gap columns"],
                [5, 34, 11, 12, 22, 60, 30, 24, 11, 60, 40, 30, 30, 9, 11])
        for i, t in enumerate(s.tables, 1):
            r += 1
            new_or_gap = sum(1 for c in t["columns"] if str(c["status"]).lower() == "new" or str(c["status"]).lower().startswith("gap"))
            _row(ws, r, [i, None, t["kind"].capitalize(), t["tier"].capitalize(), t["fact_type"], t["grain"], t["pk"], t["status_label"],
                         s.readiness(t), t["built_from"], t["in_flight"], compact_ids(self.primary.get(t["name"], [])),
                         compact_ids(self.secondary.get(t["name"], [])), len(t["columns"]), new_or_gap], fill=_table_fill(t))
            _link(ws.cell(row=r, column=2), t["name"])
            ws.cell(row=r, column=2).fill = FILL[_table_fill(t)]
            ws.cell(row=r, column=8).fill = FILL[STATUS_FILL[t["status"]]]
            ws.cell(row=r, column=9).fill = FILL[READY_FILL[s.readiness(t)]]
        ws.auto_filter.ref = f"A10:O{r}"

    def questions(self):
        s = self.spec
        ws = self.wb.create_sheet("Business questions")
        _title(ws, "Business questions and the table that answers each one",
               "'Primary table' is where the answer comes from; 'Also uses' are joins. Sources are named in the 'Where it comes from' column.")
        r = 5
        _header(ws, r, ["ID", "Theme", "Business question", "Where it comes from", "Primary table", "Core?", "Also uses", "Slice by", "How to answer", "Readiness", "Waits on"],
                [6, 18, 60, 42, 30, 8, 36, 36, 60, 11, 14])
        core = {t["name"] for t in s.core}
        for q in s.questions:
            r += 1
            _row(ws, r, [q["id"], q["theme"], q["question"], q["source"], q["primary_table"] or "(no table yet)", "Yes" if q["primary_table"] in core else "No",
                         q["also_uses"], q["slice_by"], q["how_to_answer"], q["readiness"], q["waits_on"]])
            if q["primary_table"]:
                _link(ws.cell(row=r, column=5), q["primary_table"])
                ws.cell(row=r, column=5).fill = FILL["fact" if q["primary_table"] in core else "fact_light"]
            ws.cell(row=r, column=10).fill = FILL[READY_FILL[q["readiness"]]]
        ws.auto_filter.ref = f"A5:K{r}"
        r += 2
        ws.cell(row=r, column=1, value="Coverage").font = Font(bold=True)
        for t in s.facts:
            ids = self.primary.get(t["name"], [])
            if ids:
                r += 1
                _link(ws.cell(row=r, column=2), t["name"])
                ws.cell(row=r, column=3, value=f"primary for {len(ids)} question{'s' if len(ids) != 1 else ''}: {compact_ids(ids)}")

    def bus(self):
        s = self.spec
        ws = self.wb.create_sheet("Bus matrix")
        _title(ws, "Bus matrix: fact tables by conformed dimension",
               "✓ = the fact has a key into the dimension. ◐ = it has a key, but some keys wait on the gap named. Blank = not applicable. Click a name to open its tab.")
        dims = [t["name"] for t in s.dims]
        labels = ["Tier", "Fact table", "Fact type", "Status today", "Readiness"] + dims + ["Primary for questions"]
        r = 5
        _header(ws, r, labels, [12, 34, 22, 24, 11] + [16] * len(dims) + [44])
        ws.row_dimensions[r].height = 32
        for i, dim in enumerate(dims, 6):
            _link(ws.cell(row=r, column=i), dim)
            ws.cell(row=r, column=i).fill, ws.cell(row=r, column=i).alignment = FILL["dim"], CENTER
        bus = s.bus_matrix()
        for t in sorted(s.facts, key=lambda t: t["tier"] != "core"):
            r += 1
            _row(ws, r, [t["tier"].capitalize(), None, t["fact_type"], t["status_label"], s.readiness(t)], fill=_table_fill(t))
            _link(ws.cell(row=r, column=2), t["name"])
            ws.cell(row=r, column=5).fill = FILL[READY_FILL[s.readiness(t)]]
            for i, dim in enumerate(dims, 6):
                c = ws.cell(row=r, column=i)
                c.border, c.alignment = BORDER, CENTER
                gaps = bus[t["name"]].get(dim)
                if gaps is not None:
                    c.value = ("◐ " + " ".join(gaps)) if gaps else "✓"
                    c.fill = FILL["partial" if gaps else "ok"]
            ids = self.primary.get(t["name"], [])
            c = ws.cell(row=r, column=len(labels), value=(f"{len(ids)}: " + compact_ids(ids)) if ids else "(supports other facts)")
            c.border, c.alignment = BORDER, WRAP
        ws.freeze_panes = "C6"

    def current_models(self):
        ws = self.wb.create_sheet("Current models")
        _title(ws, "Current models: what to keep, rename, merge or retire",
               "Models that exist today, on main or in flight, and what this design does with each.")
        r = 5
        _header(ws, r, ["Current model", "Grain today", "Where it lives", "Action", "Target", "Why", "In-flight work", "Used by a BI tool", "In scope"],
                [42, 44, 30, 26, 40, 80, 28, 16, 9])
        fills = [(("rename", "extend"), "rename"), (("merge", "revive", "fold"), "pr"), (("retire", "drop", "delete"), "blocked"), (("replace", "semantic"), "ok")]
        for m in self.spec.current_models:
            r += 1
            _row(ws, r, [m["model"], m["grain"], m["location"], m["action"], m["target"], m["reason"], m["in_flight"], m["bi_usage"], "Yes" if m["in_scope"] else "No"])
            a = m["action"].lower()
            ws.cell(row=r, column=4).fill = FILL[next((f for words, f in fills if a.startswith(words)), "grey")]
            tgt = m["target"].split(" (")[0].strip()
            if tgt in self.spec.by_name:
                _link(ws.cell(row=r, column=5), tgt, m["target"])
        ws.auto_filter.ref = f"A5:I{r}"

    def in_flight(self):
        ws = self.wb.create_sheet("In-flight work")
        _title(ws, "Open pull requests and branches", "Work already under way that this design builds on. The last column is the recommended next step.")
        r = 5
        _header(ws, r, ["Ref", "Title", "State", "What it adds", "How it fits this design", "Next step"], [10, 52, 24, 60, 60, 26])
        for p in self.spec.in_flight:
            r += 1
            _row(ws, r, [p.get("ref"), p.get("title"), p.get("state"), p.get("adds"), p.get("fit"), p.get("next_step")])
            if p.get("url"):
                c = ws.cell(row=r, column=1)
                c.hyperlink, c.font = p["url"], LINK
            if p.get("relevant") is False:
                for col in range(2, 7):
                    ws.cell(row=r, column=col).font = Font(color="868E96")

    def gaps(self):
        ws = self.wb.create_sheet("Gaps")
        _title(ws, "Gap register", "Each gap names the questions it blocks and the team that can close it.")
        r = 5
        _header(ws, r, ["ID", "Gap", "Blocks", "Owner", "Status", "Evidence"], [7, 60, 26, 22, 22, 90])
        for g in self.spec.gaps:
            r += 1
            _row(ws, r, [g.get("id"), g.get("gap"), g.get("blocks"), g.get("owner"), g.get("status"), g.get("evidence")])
            st = str(g.get("status", "")).lower()
            fill = "ok" if ("closed" in st and "partly" not in st) else "pr" if "flight" in st else "partial" if ("partly" in st or "new" in st) else "blocked"
            ws.cell(row=r, column=5).fill = FILL[fill]

    def decisions(self):
        ws = self.wb.create_sheet("Decisions")
        _title(ws, "Decisions needed before build", "Each decision changes a reported number. The recommendation is a default; the business owner should confirm it.")
        r = 5
        _header(ws, r, ["ID", "Decision", "Why it matters", "Options", "Recommendation"], [7, 36, 44, 60, 70])
        for x in self.spec.decisions:
            r += 1
            _row(ws, r, [x.get("id"), x.get("decision"), x.get("why"), x.get("options"), x.get("recommendation")])

    def diagrams(self):
        ws = self.wb.create_sheet("Diagrams")
        _title(ws, "Diagrams", "Editable copies are the .excalidraw files beside this workbook. Open them at excalidraw.com or in the Obsidian Excalidraw plugin.")
        row = 5
        for path in self.pngs:
            if not os.path.exists(path):
                continue
            ws.cell(row=row, column=1, value=os.path.basename(path).replace(".png", ".excalidraw")).font = Font(bold=True)
            img = Image(path)
            scale = 1400 / img.width
            img.width, img.height = int(img.width * scale), int(img.height * scale)
            ws.add_image(img, f"A{row + 1}")
            row += int(img.height / 20) + 4
        if row == 5:
            ws.cell(row=5, column=1, value="No PNG copies were rendered. Open the .excalidraw files instead.")

    def table_tab(self, t):
        s = self.spec
        ws = self.wb.create_sheet(t["name"])
        ws["A1"], ws["A1"].font = t["name"], TITLE
        _link(ws["A2"], "Summary", "← Back to Summary")
        qtext = {q["id"]: q["question"] for q in s.questions}
        meta = [("Kind", f"{t['kind'].capitalize()}  ·  {t['tier'].capitalize()}  ·  {t['fact_type']}"), ("Grain", t["grain"]),
                ("Primary key", t["pk"]), ("Status today", t["status_label"]), ("Readiness", s.readiness(t)),
                ("Built from", t["built_from"]), ("In-flight work", t["in_flight"]), ("Why it exists", t["purpose"])]
        if self.primary.get(t["name"]):
            meta.append(("Primary for", "\n".join(f"{i}  {qtext[i]}" for i in self.primary[t["name"]])))
        if self.secondary.get(t["name"]):
            meta.append(("Also used by", compact_ids(self.secondary[t["name"]])))
        r = 4
        for k, v in meta:
            ws.cell(row=r, column=1, value=k).font = Font(bold=True)
            c = ws.cell(row=r, column=2, value=v)
            ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=7)
            c.alignment = WRAP
            ws.row_dimensions[r].height = 15 * max(1, len(str(v)) // 150 + str(v).count("\n") + 1)
            r += 1
        ws.cell(row=5, column=2).fill = FILL[_table_fill(t)]
        r += 1
        head = r
        _header(ws, r, ["#", "Column", "Data type", "Role", "Description", "Lineage: where it comes from today", "Status"], [16, 40, 16, 12, 70, 58, 12])
        for i, c in enumerate(t["columns"], 1):
            r += 1
            _row(ws, r, [i, c["name"], c["type"], c["role"], c["description"], c["lineage"], c["status"]])
            ws.cell(row=r, column=7).fill = FILL[_column_status_fill(c["status"])]
            if c["role"] in ("PK", "PK part"):
                ws.cell(row=r, column=2).font = Font(bold=True)
            if c["fk"] and c["fk"] != t["name"]:
                cell = ws.cell(row=r, column=4)
                cell.hyperlink, cell.font = Hyperlink(ref=cell.coordinate, location=f"'{c['fk']}'!A1"), LINK
        ws.freeze_panes = ws.cell(row=head + 1, column=3)
        ws.auto_filter.ref = f"A{head}:G{r}"
        r += 2
        ws.cell(row=r, column=1, value="Status key").font = Font(bold=True)
        for label, fill in [("Exists: same name in a current model", "main"), ("Rename: exists under another name", "rename"),
                            ("PR #nn / Branch: on an open pull request or branch", "pr"), ("New: to build", "new"), ("Gap Gnn: null until the gap closes", "blocked")]:
            r += 1
            ws.cell(row=r, column=2, value=label).fill = FILL[fill]

    def build(self, filename):
        self.summary()
        self.questions()
        self.bus()
        self.current_models()
        self.in_flight()
        self.gaps()
        self.decisions()
        self.diagrams()
        for t in self.spec.tables:
            self.table_tab(t)
        path = os.path.join(self.out_dir, filename)
        self.wb.save(path)
        return path
