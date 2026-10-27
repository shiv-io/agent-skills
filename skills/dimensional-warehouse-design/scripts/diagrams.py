"""Excalidraw diagrams from a spec: core star schema, bus matrix, question map, model map."""
import os
import re

from excalidraw_lib import Drawing, INK, GREY, LINE, FACT, FACT_LIGHT, DIM, BRIDGE, PILL
from spec_io import compact_ids, BLOCKED, PARTIAL

SRC = "dimensional-warehouse-design"
STATUS_PILL = {"main": ("on main", "main"), "in_flight": ("in flight", "pr"), "new": ("new", "new")}
BLUE = "#1971c2"


def _wrap(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        lines.append(line)
    return lines


def _clip(text, chars):
    if len(text) <= chars:
        return text
    cut = text.rfind(" ", 0, chars - 1)
    return text[: cut if cut > chars // 2 else chars - 1].rstrip(",;:") + "…"


def _pill_for(t):
    label, kind = STATUS_PILL[t["status"]]
    return t.get("status_pill") or label, kind


def _highlights(t, limit=12):
    if t.get("highlights"):
        return t["highlights"]
    order = {"PK": 0, "PK part": 0, "FK": 1, "Milestone": 2, "Measure": 3, "Flag": 4}
    cols = sorted(t["columns"], key=lambda c: order.get(c["role"], 5))
    out = []
    for c in cols[:limit]:
        tag = f"  [{c['status'].split(' ', 1)[-1]}]" if str(c["status"]).lower().startswith("gap") else ""
        out.append(c["name"] + tag)
    return out


def _title(g, spec, text, subtitle):
    pid = spec.project.get("id", "")
    g.text(40, 30, f"{pid} {text}".strip(), size=30)
    g.text(40, 76, subtitle, size=16, color=GREY)


def star_schema(spec, out):
    g = Drawing(SRC)
    primary, _ = spec.questions_by_table()
    core = spec.core
    _title(g, spec, f"core star schema: {len(core)} fact tables carry most of the business questions",
           "Blue boxes are the core facts. Yellow boxes are conformed dimensions, shared by every fact. Light blue boxes along the bottom are supporting facts.\n"
           "A grey line means the fact has a key into that dimension. Pills show where each table stands today. [Gnn] marks a column that waits on a gap.")
    box_w, gap, x0 = 430, 40, 40
    dims = spec.dims
    half = (len(dims) + 1) // 2
    dim_top, dim_bot = dims[:half], dims[half:]
    per_row = max(len(dim_top), 1)
    total_w = max(len(core) * (box_w + gap) - gap, per_row * 410 - 30)
    dim_w = min(380, (total_w - (per_row - 1) * 30) / per_row)
    dim_gap = (total_w - per_row * dim_w) / max(per_row - 1, 1)
    anchors = {}

    def dim_height(t):
        return 70 + 19 * min(7, len(t["columns"]))

    def dim_box(t, x, y):
        h = dim_height(t)
        g.rect(x, y, dim_w, h, bg=DIM)
        g.text(x + 12, y + 10, t["name"][:30], size=20)
        label, kind = _pill_for(t)
        g.pill(x + dim_w - 12 - (len(label) * 13 * 0.55 + 16), y + 12, label, kind)
        chars = int((dim_w - 24) / (14 * 0.55))
        g.text(x + 12, y + 40, _clip("grain: " + t["grain"].split(".")[0].split(":")[0].lower(), chars - 2), size=14, color=GREY)
        g.text(x + 12, y + 64, "\n".join(c["name"] for c in t["columns"][:7]), size=14)
        return h

    fy = 200 + (max(dim_height(t) for t in dim_top) if dim_top else 0) + 90
    top_y = fy - 90 - (max(dim_height(t) for t in dim_top) if dim_top else 0)
    for i, t in enumerate(dim_top):
        x = x0 + i * (dim_w + dim_gap)
        h = dim_box(t, x, top_y)
        anchors[t["name"]] = ("top", x + dim_w / 2, top_y + h)

    fact_heights = []
    for i, t in enumerate(core):
        x = x0 + i * (box_w + gap)
        lines = _highlights(t)
        h = 150 + 19 * len(lines) + 60
        fact_heights.append(h)
        g.rect(x, fy, box_w, h, bg=FACT)
        g.text(x + 14, fy + 12, t["name"], size=21)
        px = x + 14
        px += g.pill(px, fy + 44, t["fact_type"].lower(), "none") + 8
        g.pill(px, fy + 44, *_pill_for(t))
        g.text(x + 14, fy + 78, "\n".join(_wrap("grain: " + t["grain"].split(".")[0].lower(), 48)[:3]), size=14, color=GREY)
        g.line(x, fy + 140, x + box_w, fy + 140)
        g.text(x + 14, fy + 150, "\n".join(lines), size=14)
        ids = primary.get(t["name"], [])
        ans = f"answers {len(ids)} of {len(spec.questions)}: " + compact_ids(ids)
        g.text(x + 14, fy + h - 52, "\n".join(_wrap(ans, 50)[:2]), size=14, color=BLUE)
        anchors[t["name"]] = ("fact", x + box_w / 2, fy, fy + h)

    bot_y = fy + (max(fact_heights) if fact_heights else 0) + 90
    for i, t in enumerate(dim_bot):
        x = x0 + i * (dim_w + dim_gap)
        dim_box(t, x, bot_y)
        anchors[t["name"]] = ("bot", x + dim_w / 2, bot_y)

    bus = spec.bus_matrix()
    for t in core:
        _, fx, ftop, fbot = anchors[t["name"]]
        for dim in bus.get(t["name"], {}):
            if dim not in anchors:
                continue
            side, dx, dy = anchors[dim]
            g.line(fx, ftop if side == "top" else fbot, dx, dy, color=LINE)

    sup = [t for t in spec.facts if t["tier"] != "core"]
    if sup:
        sy = bot_y + (max(dim_height(t) for t in dim_bot) if dim_bot else 0) + 70
        g.text(40, sy - 40, "Supporting facts: narrower questions, or inputs the core facts roll up", size=20)
        sw, sgap = 300, 22
        cols = max(1, int((total_w + sgap) // (sw + sgap)))
        for i, t in enumerate(sup):
            x = 40 + (i % cols) * (sw + sgap)
            y = sy + (i // cols) * 150
            g.rect(x, y, sw, 130, bg=BRIDGE if t["kind"] == "bridge" else FACT_LIGHT)
            g.text(x + 10, y + 8, t["name"][:34], size=15)
            g.pill(x + 10, y + 32, *_pill_for(t), size=12)
            g.text(x + 10, y + 60, "\n".join(_wrap(t["grain"].split(".")[0].lower(), 40)[:3]), size=12, color=GREY)
            ids = primary.get(t["name"], [])
            if ids:
                g.text(x + 10, y + 108, ("answers " + compact_ids(ids))[:44], size=12, color=BLUE)
    path = os.path.join(out, f"{spec.project.get('file_prefix', 'warehouse')}_core_star_schema.excalidraw")
    g.save(path)
    return path


def bus_matrix(spec, out):
    g = Drawing(SRC)
    primary, _ = spec.questions_by_table()
    bus = spec.bus_matrix()
    dims = [t["name"] for t in spec.dims]
    _title(g, spec, "bus matrix: fact tables x conformed dimensions",
           "Rows are fact tables, core first. A tick means the fact has a key into the dimension. A half circle means it has a key, but some of those keys wait on a gap.\n"
           "Readiness: Ready = every column has a source today. Partial = buildable now, some columns stay null until a gap closes. Blocked = the core source is not loaded yet.")
    cols = [("Tier", 110), ("Fact table", 330), ("Fact type", 200), ("Today", 140), ("Readiness", 110)]
    cols += [(spec.dim_label(d).replace(" ", "\n", 1) if len(spec.dim_label(d)) > 11 else spec.dim_label(d), 104) for d in dims]
    cols += [("Primary for questions", 470)]
    x, y, hh, rh = 40, 140, 64, 44
    xs = []
    for label, w in cols:
        xs.append((x, w))
        g.rect(x, y, w, hh, bg="#e9ecef", stroke_width=1)
        g.text(x + 8, y + 10, label, size=15)
        x += w
    y += hh
    facts = sorted(spec.facts, key=lambda t: t["tier"] != "core")
    for t in facts:
        bg_row = FACT if t["tier"] == "core" else (BRIDGE if t["kind"] == "bridge" else FACT_LIGHT)
        for (cx, w), val in zip(xs[:4], [t["tier"].capitalize(), t["name"], t["fact_type"], _pill_for(t)[0]]):
            g.rect(cx, y, w, rh, bg=bg_row, stroke_width=1)
            g.text(cx + 8, y + 12, val, size=14)
        r = spec.readiness(t)
        cx, w = xs[4]
        g.rect(cx, y, w, rh, bg=PILL["blocked" if r == BLOCKED else "partial" if r == PARTIAL else "ok"], stroke_width=1)
        g.text(cx + 8, y + 12, r, size=14)
        for (cx, w), dim in zip(xs[5:5 + len(dims)], dims):
            gaps = bus[t["name"]].get(dim)
            if gaps is None:
                g.rect(cx, y, w, rh, bg="#ffffff", stroke_width=1)
            elif gaps:
                g.rect(cx, y, w, rh, bg=PILL["partial"], stroke_width=1)
                g.text(cx + w / 2, y + 4, "◐\n" + " ".join(gaps), size=13, align="center")
            else:
                g.rect(cx, y, w, rh, bg=PILL["ok"], stroke_width=1)
                g.text(cx + w / 2, y + 10, "✓", size=18, align="center")
        cx, w = xs[-1]
        ids = primary.get(t["name"], [])
        g.rect(cx, y, w, rh, bg="#ffffff", stroke_width=1)
        g.text(cx + 8, y + 12, ((f"{len(ids)}: " + compact_ids(ids)) if ids else "(supports others)")[:62], size=13)
        y += rh
    n, total = spec.core_share()
    if total:
        g.text(40, y + 24, f"The {len(spec.core)} core facts are the primary table for {n} of the {total} business questions ({n / total:.0%}).", size=16, color=INK)
    path = os.path.join(out, f"{spec.project.get('file_prefix', 'warehouse')}_bus_matrix.excalidraw")
    g.save(path)
    return path


def question_map(spec, out):
    g = Drawing(SRC)
    primary, _ = spec.questions_by_table()
    _title(g, spec, "question map: which fact table answers each family of business questions",
           "Left: the question families from the source documents, with question ids from the workbook's 'Business questions' tab.\n"
           "Right: the fact table that is primary for those questions. The blue line inside each box counts the questions per table. Blue arrows go to core facts, grey to supporting facts.")
    themes = []
    for q in spec.questions:
        if q["theme"] not in themes:
            themes.append(q["theme"])
    tags = [s["tag"] for s in spec.project.get("sources", []) if s.get("tag")]
    lx, ly, lw, lh, lgap = 40, 160, 620, 128, 18
    rx, rw, rh, rgap = 1300, 420, 84, 40
    tables = [t["name"] for t in spec.core] + [t["name"] for t in spec.facts if t["tier"] != "core" and t["name"] in primary]
    tpos, ry = {}, ly
    for i, name in enumerate(tables):
        t = spec.by_name[name]
        if i == len(spec.core) and i:
            ry += 30
            g.text(rx, ry - 30, "supporting", size=14, color=GREY)
        g.rect(rx, ry, rw, rh, bg=FACT if t["tier"] == "core" else FACT_LIGHT)
        g.text(rx + 12, ry + 10, name[:36], size=18)
        n = len(primary.get(name, []))
        g.text(rx + 12, ry + 40, f"primary for {n} question{'s' if n != 1 else ''}", size=14, color=GREY)
        tpos[name] = (rx, ry + rh / 2)
        ry += rh + rgap
    for i, theme in enumerate(themes):
        y = ly + i * (lh + lgap)
        qs = [q for q in spec.questions if q["theme"] == theme]
        g.rect(lx, y, lw, lh, bg="#f8f9fa")
        g.text(lx + 12, y + 10, theme[:50], size=18)
        g.text(lx + 12, y + 40, compact_ids([q["id"] for q in qs])[:80], size=14, color=GREY)
        found = [tg for tg in tags if any(tg.lower() in q["source"].lower() for q in qs)]
        if found:
            g.text(lx + 12, y + 62, "from: " + ", ".join(found), size=12, color=GREY)
        counts = {}
        for q in qs:
            if q["primary_table"]:
                counts[q["primary_table"]] = counts.get(q["primary_table"], 0) + 1
        ordered = sorted(counts.items(), key=lambda kv: -kv[1])
        summary = ", ".join(f"{k.removeprefix('fct_')} {v}" for k, v in ordered)
        g.text(lx + 12, y + 84, "\n".join(_wrap(summary.replace(", ", ", "), 84)[:2]).replace(" ", " "), size=12, color=BLUE)
        for name, n in ordered:
            if name not in tpos:
                continue
            tx, ty = tpos[name]
            core = spec.by_name[name]["tier"] == "core"
            g.line(lx + lw, y + lh / 2, tx, ty, color=BLUE if core else LINE, width=2 if core else 1, arrow=True)
    path = os.path.join(out, f"{spec.project.get('file_prefix', 'warehouse')}_question_map.excalidraw")
    g.save(path)
    return path


ACTION_COLOURS = [
    (("rename", "extend"), BLUE), (("merge", "revive", "fold"), "#9c36b5"), (("retire", "drop", "delete"), "#e03131"),
    (("replace", "semantic"), "#0c8599"), (("keep", "move"), "#868e96"),
]


def _action_colour(action):
    a = action.lower()
    for words, colour in ACTION_COLOURS:
        if any(a.startswith(w) for w in words):
            return colour
    return "#868e96"


def _targets(m):
    raw = m["target"].strip()
    if raw.lower() in ("same", ""):
        return [m["model"].split(",")[0].strip() + " (unchanged)"]
    if raw.lower() == "none":
        return ["(dropped)"]
    return [t.strip() for t in re.split(r"[+,]", raw) if t.strip()]


def model_map(spec, out):
    if not spec.current_models:
        return None
    g = Drawing(SRC)
    _title(g, spec, "model map: today's models -> the target warehouse",
           "Left: models that exist today, on main or in flight. Right: the target table. Arrow colour is the action; dashed arrows retire a model.\n"
           "Orange boxes on the right are new tables with no current model. Models outside the scope of this design are listed at the bottom.")
    legend = [("Rename / extend", BLUE), ("Merge / revive", "#9c36b5"), ("Retire / drop", "#e03131"), ("Replace with semantic view", "#0c8599"), ("Keep", "#868e96")]
    lx = 40
    for label, colour in legend:
        g.line(lx, 150, lx + 40, 150, color=colour, width=3, arrow=True)
        g.text(lx + 48, 140, label, size=14)
        lx += 48 + len(label) * 14 * 0.55 + 40
    in_scope = [m for m in spec.current_models if m["in_scope"]]
    out_scope = [m for m in spec.current_models if not m["in_scope"]]
    left_x, left_w, row_h, row_gap, top = 40, 560, 54, 14, 190
    right_x, right_w = 1240, 470
    targets = []
    for m in in_scope:
        for tgt in _targets(m):
            if tgt not in targets:
                targets.append(tgt)
    new_tables = [t["name"] for t in spec.tables if t["name"] not in targets and t["status"] == "new"]
    tpos, y = {}, top
    for tgt in targets + new_tables:
        known = spec.by_name.get(tgt)
        if tgt in new_tables:
            bg = PILL["new"]
        elif known and known["tier"] == "core":
            bg = FACT
        elif known and known["kind"] == "dimension":
            bg = DIM
        elif known:
            bg = FACT_LIGHT
        else:
            bg = "#f1f3f5"
        g.rect(right_x, y, right_w, row_h - 10, bg=bg, stroke_width=1)
        g.text(right_x + 10, y + 12, tgt[:52], size=15)
        tpos[tgt] = (right_x, y + (row_h - 10) / 2)
        y += row_h
    y = top
    for m in in_scope:
        colour = _action_colour(m["action"])
        g.rect(left_x, y, left_w, row_h, bg="#f8f9fa", stroke_width=1)
        g.text(left_x + 10, y + 6, m["model"][:58], size=15)
        g.text(left_x + 10, y + 28, (m["location"] + "  |  " + m["action"])[:74], size=12, color=GREY)
        for tgt in _targets(m):
            tx, ty = tpos[tgt]
            g.line(left_x + left_w, y + row_h / 2, tx, ty, color=colour, width=2, arrow=True,
                   dashed=m["action"].lower().startswith(("retire", "drop", "delete")))
        y += row_h + row_gap
    y = max(y, top + len(tpos) * row_h) + 30
    if out_scope:
        g.text(40, y, "Unchanged by this design (out of scope, or application payloads):", size=16)
        g.text(40, y + 28, "\n".join(f"{m['model']}  ->  {m['action'].lower()}" for m in out_scope), size=13, color=GREY)
    path = os.path.join(out, f"{spec.project.get('file_prefix', 'warehouse')}_model_map.excalidraw")
    g.save(path)
    return path


def build_all(spec, out):
    paths = [star_schema(spec, out), bus_matrix(spec, out), question_map(spec, out), model_map(spec, out)]
    return [p for p in paths if p]
