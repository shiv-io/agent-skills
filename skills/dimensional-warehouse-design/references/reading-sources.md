# Reading source documents

## KPI and reporting spreadsheets

Run:

```bash
uv run <skill-dir>/scripts/extract_spreadsheet.py "<file>.xlsx" --out <scratch>/outline.md
```

The outline lists every tab and how it was read:

- **Summary / model tabs**: every labelled row with its first value and first formula.
- **Raw data tabs**: the source note rows and the header row only. A tab counts as raw when it has 300
  or more filled rows, or when it contains record identifiers (UUIDs, emails, phone numbers, long numeric
  ids). Override with `--raw "<tab>"` or `--summary "<tab>"`.

Never open a raw data tab's rows to read them. They usually hold customer, member or patient records. If
you need to know what values a column takes, profile the same data in the warehouse with aggregates.

What to take from the outline:

| Look for | Why |
|---|---|
| `COUNTIFS` / `SUMIFS` over a raw tab | The real metric definition: which column, which filter values. For example, "visit type = Initial Consultation AND billable flag = 1 AND status = Occurred". |
| Note rows on raw tabs ("Source: <BI workbook URL>", "Last updated") | Which BI asset feeds the sheet today. That asset is a current model to inventory. |
| Hard-coded exclusions ("exclude weeks with > 1000 hits", "outlier") | A rule someone applies by hand. Each one becomes a decision with a modelled replacement. |
| Separate tabs per segment (for example one per care model or product line) | A dimension the warehouse must carry, and often a definition that differs by segment (two "new customer" rules). |
| Plan, forecast, assumption and rate tabs | Numbers that live only in the spreadsheet. They become seeds with an owner, or a gap. |
| Window lengths ("within 7 days", "21-day CVR", "30/60/90 days") | Columns on an accumulating snapshot (days between milestones) plus an observed-days column for maturity. |
| "Baked" versus "baking" cohorts | The design needs an observed-since column so incomplete cohorts can be flagged. |
| Empty placeholder tabs | Questions the team wants answered but cannot yet. Include them. |

Excel's `max_row` counts formatted empty rows, so a summary tab can claim a thousand rows while holding
fifty. The extractor counts filled rows instead.

## Memos, decks and documents

- Pull every metric with its current value, target and benchmark. These become questions and, often,
  semantic-view metrics.
- Pull every named hypothesis ("lead time drives no-shows", "evening slots attend less"). Each implies a
  slice the fact table must support (lead-time band, local hour).
- Pull every "we do not know" or "we cannot see". Each is a gap, with the owner the document names.
- Note interventions with dates. They become analysis periods in the date dimension, so before-and-after
  comparisons need no hard-coded dates.

## Tickets

Read the ticket, its parent, and anything it links. Tickets carry the decision the design feeds and
sometimes the prior design to build on.
