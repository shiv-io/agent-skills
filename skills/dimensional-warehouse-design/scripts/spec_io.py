"""Load and validate a warehouse design spec (YAML or JSON), and derive shared values."""
import json
import re
import sys

FACT_KINDS = ("fact", "bridge")
READY, PARTIAL, BLOCKED = "Ready", "Partial", "Blocked"


class SpecError(ValueError):
    pass


def load(path):
    with open(path) as f:
        text = f.read()
    if path.endswith((".yaml", ".yml")):
        import yaml
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise SpecError(f"{path} is not valid YAML: {e}. Quote any value that holds ': ' or starts with a quote.")
    else:
        data = json.loads(text)
    return Spec(data)


def _as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [s.strip() for s in re.split(r"[,;]", v) if s.strip()]
    return list(v)


class Spec:
    def __init__(self, data):
        self.raw = data
        self.project = data.get("project", {})
        self.tables = [self._table(t) for t in data.get("tables", [])]
        self.by_name = {t["name"]: t for t in self.tables}
        self.questions = [self._question(q) for q in data.get("questions", [])]
        self.current_models = [self._model(m) for m in data.get("current_models", [])]
        self.in_flight = data.get("in_flight", [])
        self.gaps = data.get("gaps", [])
        self.decisions = data.get("decisions", [])
        self.validate()

    # ---------------------------------------------------------------- shape
    @staticmethod
    def _table(t):
        t = dict(t)
        t["kind"] = t.get("kind", "fact").lower()
        t.setdefault("tier", "conformed" if t["kind"] == "dimension" else "supporting")
        t["tier"] = t["tier"].lower()
        t.setdefault("fact_type", "Dimension" if t["kind"] == "dimension" else "Transaction")
        t.setdefault("status", "new")
        t.setdefault("status_label", {"main": "On main", "in_flight": "In flight", "new": "New"}.get(t["status"], t["status"]))
        for k in ("built_from", "in_flight", "purpose", "pk", "grain"):
            t.setdefault(k, "")
        t.setdefault("source_in_flight", False)
        t.setdefault("bus_gaps", {})
        t["columns"] = [Spec._column(c) for c in t.get("columns", [])]
        return t

    @staticmethod
    def _column(c):
        if isinstance(c, (list, tuple)):
            keys = ("name", "type", "role", "description", "lineage", "status", "fk")
            c = dict(zip(keys, c))
        c = dict(c)
        c.setdefault("type", "VARCHAR")
        c.setdefault("role", "Attribute")
        c.setdefault("description", "")
        c.setdefault("lineage", "")
        c.setdefault("status", "New")
        c.setdefault("fk", None)
        return c

    @staticmethod
    def _question(q):
        q = dict(q)
        q["also_uses"] = _as_list(q.get("also_uses"))
        q["waits_on"] = _as_list(q.get("waits_on"))
        q.setdefault("readiness", READY)
        for k in ("theme", "source", "slice_by", "how_to_answer", "primary_table"):
            q.setdefault(k, "")
        return q

    @staticmethod
    def _model(m):
        m = dict(m)
        m.setdefault("in_scope", True)
        for k in ("grain", "location", "action", "target", "reason", "in_flight", "bi_usage"):
            m.setdefault(k, "")
        return m

    # ------------------------------------------------------------ validation
    def validate(self):
        errors = []
        names = [t["name"] for t in self.tables]
        dupes = {n for n in names if names.count(n) > 1}
        if dupes:
            errors.append(f"duplicate table names: {sorted(dupes)}")
        for t in self.tables:
            if len(t["name"]) > 31:
                errors.append(f"{t['name']}: longer than 31 characters, which Excel refuses as a tab name")
            if t["kind"] not in ("fact", "bridge", "dimension"):
                errors.append(f"{t['name']}: kind must be fact, bridge or dimension")
            if t["status"] not in ("main", "in_flight", "new"):
                errors.append(f"{t['name']}: status must be main, in_flight or new")
            cols = [c["name"] for c in t["columns"]]
            if len(cols) != len(set(cols)):
                errors.append(f"{t['name']}: duplicate column names")
            for c in t["columns"]:
                if c["fk"] and c["fk"] not in self.by_name:
                    errors.append(f"{t['name']}.{c['name']}: fk points at unknown table {c['fk']}")
        ids = [q["id"] for q in self.questions]
        if len(ids) != len(set(ids)):
            errors.append("duplicate question ids")
        for q in self.questions:
            if q["primary_table"] and q["primary_table"] not in self.by_name:
                errors.append(f"{q['id']}: primary_table {q['primary_table']} is not a table in the spec")
            if q["readiness"] not in (READY, PARTIAL, BLOCKED):
                errors.append(f"{q['id']}: readiness must be Ready, Partial or Blocked")
        if errors:
            raise SpecError("spec has problems:\n  - " + "\n  - ".join(errors))

    # --------------------------------------------------------------- derived
    @property
    def facts(self):
        return [t for t in self.tables if t["kind"] in FACT_KINDS]

    @property
    def core(self):
        return [t for t in self.tables if t["tier"] == "core"]

    @property
    def dims(self):
        return [t for t in self.tables if t["kind"] == "dimension"]

    def dim_label(self, name):
        t = self.by_name[name]
        return t.get("label") or name.removeprefix("dim_").replace("_", " ").capitalize()

    def readiness(self, t):
        if t.get("readiness"):
            return t["readiness"]
        if t["source_in_flight"]:
            return BLOCKED
        if any(str(c["status"]).lower().startswith("gap") for c in t["columns"]):
            return PARTIAL
        return READY

    def bus_matrix(self):
        """{fact: {dim: sorted gap ids}}; an empty list means a clean key."""
        out = {}
        for t in self.facts:
            row = {}
            for c in t["columns"]:
                if c["fk"] and self.by_name[c["fk"]]["kind"] == "dimension":
                    gaps = row.setdefault(c["fk"], set())
                    if str(c["status"]).lower().startswith("gap"):
                        gaps.add(str(c["status"]).split(" ", 1)[-1])
            for dim, extra in t["bus_gaps"].items():
                row.setdefault(dim, set()).update(_as_list(extra))
            out[t["name"]] = {k: sorted(v) for k, v in row.items()}
        return out

    def questions_by_table(self):
        primary, secondary = {}, {}
        for q in self.questions:
            if q["primary_table"]:
                primary.setdefault(q["primary_table"], []).append(q["id"])
            for other in q["also_uses"]:
                if other in self.by_name and self.by_name[other]["kind"] in FACT_KINDS:
                    secondary.setdefault(other, []).append(q["id"])
        return primary, secondary

    def core_share(self):
        primary, _ = self.questions_by_table()
        n = sum(len(primary.get(t["name"], [])) for t in self.core)
        return n, len(self.questions)


def compact_ids(ids):
    """Q04 Q06 Q07 Q08 -> Q04 Q06-Q08. Ids that are not prefix+number are kept as they are."""
    parsed, other = [], []
    for i in ids:
        m = re.fullmatch(r"([A-Za-z]+)(\d+)", i)
        (parsed.append((m.group(1), int(m.group(2)), len(m.group(2)))) if m else other.append(i))
    parsed.sort()
    out, run = [], []
    for p in parsed + [None]:
        if run and (p is None or p[0] != run[-1][0] or p[1] != run[-1][1] + 1):
            a, b = run[0], run[-1]
            fmt = lambda x: f"{x[0]}{x[1]:0{x[2]}d}"
            out.append(fmt(a) if a == b else f"{fmt(a)}-{fmt(b)}")
            run = []
        if p is not None:
            run.append(p)
    return " ".join(out + other)


if __name__ == "__main__":
    s = load(sys.argv[1])
    n, total = s.core_share()
    print(f"ok: {len(s.tables)} tables, {len(s.questions)} questions, core facts primary for {n}/{total}")
