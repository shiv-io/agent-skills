# <ID>: <title>

**Version <n>, <date>.** <One sentence on what this builds on, for example a prior design.>

## What is here

| File | What it holds |
|---|---|
| `<prefix>_warehouse_design.xlsx` | Summary of every table, linked to one tab per table, plus business questions, bus matrix, current models, in-flight work, gaps, decisions and diagrams. |
| `<prefix>_core_star_schema.excalidraw` / `.png` | Core facts, conformed dimensions, supporting facts. |
| `<prefix>_bus_matrix.excalidraw` / `.png` | Facts by dimensions, with readiness. |
| `<prefix>_question_map.excalidraw` / `.png` | Question families mapped to facts. |
| `<prefix>_model_map.excalidraw` / `.png` | Current models mapped to target tables. |
| `<prefix>_design_spec.yaml` | The single source for all of the above. Edit it and rebuild. |

Rebuild:

```bash
uv run <skill-dir>/scripts/build.py <prefix>_design_spec.yaml --out .
```

## The design in one paragraph

<N> core fact tables answer <n> of the <total> business questions (<share>). <One sentence per core fact:
what one row is and what it answers.> <Supporting facts and dimensions in one sentence.>

## Facts we proved

- <Something checked in the warehouse or read in a source, with the check in plain words.>

## Guesses that need checking

- <Something inferred, and how to test it.>

## What still needs a decision

1. **D<n>**: <decision>. <Why it changes a headline number.>

## Recommended order of work

1. <Unblock the source that loses history every day it waits.>
2. <Merge or extend in-flight work the design builds on.>
3. <Build the core facts, then the metric layer, after the decisions are agreed.>
