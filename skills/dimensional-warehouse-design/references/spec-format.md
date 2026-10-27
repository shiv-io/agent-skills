# Spec format

One YAML (or JSON) file drives every output. Start from `assets/example_spec.yaml`. Validate any time
with:

```bash
uv run --with pyyaml python <skill-dir>/scripts/spec_io.py <spec>.yaml
```

Use block style. Inline `{key: value, ...}` mappings break as soon as a value holds a comma or a colon.
Quote any value that holds `: ` or starts with a quote.

## project

```yaml
project:
  id: ABC-123                # ticket or engagement id; prefixes diagram titles
  title: Warehouse design for the operations scorecard
  file_prefix: abc-123       # output file names: <file_prefix>_warehouse_design.xlsx and so on
  version: "1"
  date: 1 March 2027
  warehouse: Snowflake
  sources:                   # tag is matched against each question's source text for the question map
    - tag: Scorecard
      description: Operations scorecard spreadsheet (February 2027)
```

## tables

```yaml
tables:
  - name: fct_visits                 # 31 characters at most: it becomes an Excel tab name
    kind: fact                       # fact | dimension | bridge
    tier: core                       # core | supporting (facts); dimensions default to conformed
    fact_type: Accumulating snapshot # Transaction | Accumulating snapshot | Periodic snapshot | Bridge (type 2) | Dimension
    grain: One row per scheduled visit, all outcomes.   # first sentence is used on diagrams
    pk: visit_id                     # comma-separated for a composite key
    status: main                     # main | in_flight | new  (drives the pill colour)
    status_label: On main, rename    # free text shown in the workbook (optional)
    source_in_flight: false          # true marks the table Blocked until its source lands
    built_from: visits (rename), stg_ehr__appointments
    in_flight: "#14 (referral staging)"
    purpose: Why the table exists, in one or two sentences.
    label: Visit                     # dimensions only: short label for bus matrix headers
    highlights: [...]                # core facts only, optional: 10-14 lines for the star schema box
    bus_gaps:                        # optional: a gap that applies to a fact-dimension pair
      dim_booking_channels: [G1]     #   even though the key column itself has a source
    columns:
      - name: clinic_id
        type: VARCHAR
        role: FK                     # PK | PK part | FK | Degenerate | Milestone | Measure | Flag | Attribute
        fk: dim_clinics              # target table; drives the bus matrix, diagram lines and links
        description: The clinic the visit was booked at. Joins to dim_clinics.
        lineage: visits.location_id  # where the value comes from today
        status: Rename               # Exists | Rename | New | PR #nn | Branch | Gap Gnn
```

Readiness is derived: Blocked when `source_in_flight` is true, Partial when any column has a `Gap`
status, otherwise Ready. Set `readiness:` on a table to override.

## questions

```yaml
questions:
  - id: Q01
    theme: Volume
    question: How many visits occurred each week by clinic?
    source: "Scorecard: Weekly volume"
    primary_table: fct_visits        # empty when no table can answer it yet
    also_uses: [dim_clinics]
    slice_by: week, clinic
    how_to_answer: Count did_occur by week_start_on and clinic.
    readiness: Ready                 # Ready | Partial | Blocked
    waits_on: [G2, D1]
```

## current_models

```yaml
current_models:
  - model: visits
    grain: One row per visit
    location: main / core            # or "PR #59", "branch <name>"
    action: Rename and extend        # starts with rename, extend, merge, revive, fold, replace, retire, drop, keep or move
    target: fct_visits               # "a + b" for several; "same" for unchanged; "none" for dropped
    reason: Already the visit grain.
    in_flight: ""
    bi_usage: "Yes"
    in_scope: true                   # false lists it under "unchanged" on the model map
```

## in_flight, gaps, decisions

```yaml
in_flight:
  - {ref: "#14", title: ..., state: Open, adds: ..., fit: ..., next_step: Merge, url: ..., relevant: true}
gaps:
  - {id: G1, gap: ..., blocks: "Q03, Q04", owner: Intake team, status: Open, evidence: ...}
decisions:
  - {id: D1, decision: ..., why: ..., options: ..., recommendation: ...}
```

(Inline mappings are shown here for brevity. Write them in block style in a real spec.)
