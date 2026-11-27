# Workflow in detail

Each phase lists what to produce and how to know it is done.

## 1. Read the sources

Produce a short list per source: the metrics it reports, how each is computed, the filters and
exclusions it applies, the targets and benchmarks, and the questions it asks or implies.

- Spreadsheets: run `scripts/extract_spreadsheet.py` and read the outline. See `reading-sources.md`.
- Memos and decks: read the headings first, then every table. Targets ("70% by December"), benchmarks
  and named owners are requirements too.
- Tickets: read the ticket and any linked tickets or documents. A ticket often names the decision the work
  feeds.
- A prior design: read it fully. Continue its gap and decision numbering, so ids stay stable across
  versions. Copy its diagrams into a `reference/` folder beside the new outputs; do not move or delete them.

Done when every number on every summary tab traces to a definition you can state in one sentence.

## 2. Inventory what exists

Produce an inventory file (markdown, plus a CSV of every column) in a scratch folder. See `inventory.md`.

Done when you can say, for every current model: its grain, its key, what it reads, and whether something
else already holds the same rows.

## 3. Write the business questions

- Aim for 30-60. Fewer than 20 usually means a theme was missed; more than 80 usually means one question
  was split into variants.
- Group into themes that follow the business, for example volume, conversion, retention, operations,
  quality, supply, revenue.
- Each question has: id (`Q01`), theme, the question in plain words, where it comes from (tab or section
  name), the primary table, other tables it joins, what to slice by, how to answer it in one sentence,
  readiness (Ready, Partial, Blocked) and what it waits on (gap or decision ids).
- Include the questions the sources imply but do not ask. For example, a placeholder tab called
  "Engagement" with three empty rows is still three questions.

## 4. Design

Follow `modelling-rules.md`. In order:

1. List the business processes the questions touch.
2. Choose the core facts. Count questions per candidate. Adjust until a limited set of facts carries about 80-90% — the right number differs for every business.
3. Add supporting facts for the remaining questions, and for inputs the core facts roll up.
4. Define the conformed dimensions. Put definitional rules (outcome groups, billable types, traffic
   classification) in small seed-backed dimensions so each rule lives once.
5. Map every current model to an action: keep, rename, extend, merge, replace with a semantic view,
   retire, drop, or move out of the warehouse layer.
6. Fold in-flight work into the design instead of duplicating it. If an open PR builds half a table, the
   design extends that PR's table.
7. Write the gap register and the decision list.

Before calling anything a gap, profile the source: fill rate, distinct values, date range. A field that
looks missing is often present under another name or in a newer source.

## 5. Write the spec

See `spec-format.md`. Write it in the client's output folder as `<prefix>_design_spec.yaml`. Keep
descriptions to one or two sentences, written for a business user.

## 6. Build and check

```bash
uv run <skill-dir>/scripts/build.py <prefix>_design_spec.yaml --out <output-dir>
```

Then look at every PNG. Common fixes:

| Problem in the PNG | Fix in the spec |
|---|---|
| Lines spill out of a core fact box | Set `highlights` on the table: 10-14 short lines, combining related columns ("visit_1_at ... visit_5_at"). |
| Grain text clipped | Shorten the first sentence of `grain`. The diagram uses only the first sentence. |
| A dimension missing from the star | Check that the fact's key column has `fk: dim_name`. |
| A question family points nowhere | Its questions have no `primary_table`. |

## 7. Write the design note

Copy `assets/design_note_template.md`. Keep facts, guesses and open decisions in separate sections.

## 8. Report

Lead with the core facts and their share of the questions. Then the redundancies found, the decisions
needed, and the recommended order of work. Name the output paths.
