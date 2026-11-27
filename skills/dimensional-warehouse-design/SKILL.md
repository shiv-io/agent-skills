---
name: dimensional-warehouse-design
description: Design a Kimball-style data warehouse (fact and dimension tables) from a client's source documents, such as KPI spreadsheets, metric memos, tickets and lists of business questions, and from what already exists in their warehouse. Produces a hyperlinked Excel design workbook (summary of every table, one tab per table with columns, types and descriptions, business questions mapped to tables, bus matrix, keep/rename/merge/retire list for current models, in-flight work, gaps, decisions) and Excalidraw diagrams with PNG copies. Use when asked to scope or design a warehouse, a fact/dimension model, a bus matrix or a semantic layer for a set of metrics, or to replace manual KPI spreadsheets with modelled tables.
license: MIT
metadata:
  author: shiv-io
  version: "1.0.0"
---

# Dimensional warehouse design

Turn a pile of source documents ("this is how we report today") into a warehouse design that a data
team can build and a business owner can review. The design centres on **a limited set of core fact tables that answer 80-90% of the business questions**, with supporting facts and conformed dimensions for the
rest. How many that is differs for every business — the point is the set stays limited, not unlimited.

The inputs change with every client. The outputs stay the same:

| Output | What it is |
|---|---|
| `<prefix>_warehouse_design.xlsx` | Summary tab listing every table, each hyperlinked to its own tab (grain, key, lineage, questions answered, every column with type, role, description, lineage, status). Plus tabs for business questions, bus matrix, current models, in-flight work, gaps, decisions and diagrams. |
| `<prefix>_core_star_schema.excalidraw` | Core facts, conformed dimensions, supporting facts. |
| `<prefix>_bus_matrix.excalidraw` | Facts by dimensions, readiness, questions per fact. |
| `<prefix>_question_map.excalidraw` | Question families mapped to the fact that answers them. |
| `<prefix>_model_map.excalidraw` | Today's models mapped to the target tables, coloured by action. |
| `<prefix>_warehouse_design.md` | A short design note: facts proved, guesses, decisions, order of work. |

Each `.excalidraw` also gets a `.png` copy, which the workbook embeds.

## Inputs to ask for

Work with whatever the user provides. Ask once, briefly, only for what is missing and changes the design:

1. **Source documents.** KPI or reporting spreadsheets, memos, tickets, board decks, metric definitions,
   lists of questions. These are the requirements.
2. **The current warehouse.** Read access (Snowflake, BigQuery, Databricks, Postgres) and the
   transformation repo (dbt or similar), if one exists.
3. **Work in flight.** Open pull requests and branches in that repo. Check them yourself with `gh` when the
   repo is on GitHub.
4. **A prior design**, if one exists, to build on rather than restart.
5. **Where outputs go.** A folder in the client's project, never this skill's folder.

## Workflow

Follow these phases in order. `references/workflow.md` has the detail for each one.

1. **Read the sources.** For spreadsheets, run `scripts/extract_spreadsheet.py`. It prints labels and
   formulas from summary tabs, and only headers from raw-data tabs, so customer or patient rows never
   enter your context. Formulas are the clearest statement of how a metric is computed today. For memos,
   pull out every metric, target, benchmark and question. See `references/reading-sources.md`.
2. **Inventory what exists.** Every model, its grain, key, row count, columns and comments, its upstream
   models, and whether a BI tool reads it. Note overlaps, names that do not match their grain, and tables
   built outside the transformation repo. Include open PRs and unmerged branches. This is broad, noisy
   work. Delegate it to a subagent if your agent supports one, and keep only the findings. See
   `references/inventory.md`.
3. **Write the business questions.** Usually 30-60, grouped into themes, each traced to a source and
   phrased as a business user would ask it.
4. **Design.** Choose the core facts, then the supporting facts, the conformed dimensions, and the
   decisions and gaps. Reuse and rename before you build new. Profile a source before you call it a gap.
   Follow `references/modelling-rules.md`.
5. **Write the spec.** One YAML file in the client's output folder. It is the single source for every
   output. See `references/spec-format.md`, and copy `assets/example_spec.yaml` as a starting point.
6. **Build and check.**
   ```bash
   uv run <skill-dir>/scripts/build.py <output-dir>/<prefix>_design_spec.yaml --out <output-dir>
   ```
   The build checks itself: every internal link resolves, and every table tab lists every column. Then
   open each PNG and look at it. Fix overflow, clipped text and crossing labels in the spec (shorter
   `highlights`, shorter grain sentences) and rebuild.
7. **Write the design note** from `assets/design_note_template.md`.
8. **Report.** Give the core facts and what share of questions they carry, the main redundancies, the
   decisions the business owner must make, and the recommended order of work.

## Rules that matter most

- **Name things for what they are.** A table name says what one row is. A column name says what one value
  is, with its unit. If a current name disagrees with its content, propose the rename and say why.
- **Core facts carry the weight.** Pick a limited set — the right number differs for every business, so don't aim for a particular count. Count the questions each one is primary for, and
  report the share. If it is under about 80%, the core set is wrong or the questions are too scattered.
- **One definition, one place.** A rule such as "billable", "new customer" or "active" lives in one
  dimension or one column, never restated downstream. Ambiguous rules become decisions in the workbook,
  with a recommended default.
- **Facts versus guesses.** Anything stated as a fact was checked in the warehouse or read in a source.
  Label everything else as a guess, and list what still needs testing.
- **No sensitive data in outputs.** No PHI, PII, member identifiers or real names in the spec, the
  workbook, the diagrams or any description. Row counts and dates belong in the design note or a PR, not
  in column descriptions, because descriptions outlive the numbers.
- **Client isolation.** Client files, specs and outputs stay in the client's project. Never write them into
  this skill's directory or repository.

## Requirements

- `uv`. The scripts declare their own dependencies inline (openpyxl, pillow, pyyaml).
- `excalidraw-cli` for PNG copies: `npm i -g @swiftlysingh/excalidraw-cli`. Without it, `build.py` tries
  `npx`, and otherwise skips the PNGs.
