# Inventorying the current warehouse

The goal is to know what exists, what can be reused or renamed, and what is redundant, before designing
anything new. Delegate this to a subagent where possible. It reads a lot and only the conclusions matter.

## What to collect

1. **Every published model** (marts, or whatever the reporting layer is called): name, folder, grain
   (from its docs or first-line comment), primary key (from uniqueness tests), row count, upstream models,
   and whether a BI tool reads it.
2. **Every column** of those models with type and persisted comment, as a CSV: schema, table, ordinal,
   column, data type, comment. The design's lineage column cites these.
3. **Intermediate models** with a one-line purpose each.
4. **Objects not built by the repo**: views or tables in the reporting schemas that no model creates
   (orphans of removed models, hand-built tables, dynamic tables, semantic views in developer databases).
5. **Work in flight**: open pull requests (`gh pr list --state open`), unmerged branches, local worktrees.
   For each, what models it adds and whether it is stacked on another.
6. **Source coverage**: which raw sources exist for each subject area, which are modelled, and which are
   not. This is what makes a new fact feasible or blocked.

## Useful queries

Warehouse catalogs differ; the shape is the same everywhere.

```sql
-- tables, row counts, comments in the reporting schema
select table_schema, table_name, row_count, comment
from <db>.information_schema.tables
where table_schema in ('MART', 'INT')
order by 1, 2;

-- every column with its comment
select table_schema, table_name, ordinal_position, column_name, data_type, comment
from <db>.information_schema.columns
where table_schema = 'MART'
order by 1, 2, 3;
```

In Snowflake, `get_ddl('table', '<fqn>')` recovers the SQL of a dynamic table or view built outside the
repo. In dbt projects, `target/manifest.json` gives every model's tests, refs and description without a
warehouse query.

## Redundancy checks

Prove an overlap before recommending a merge or a retirement:

```sql
-- do two tables hold the same set of keys?
select
  count_if(a.key is not null and b.key is null) as only_in_a,
  count_if(a.key is null and b.key is not null) as only_in_b,
  count_if(a.key is not null and b.key is not null) as in_both
from (select distinct <key> as key from <table_a>) a
full outer join (select distinct <key> as key from <table_b>) b on a.key = b.key;
```

Common redundancies:

| Pattern | Usual action |
|---|---|
| Two tables at the same grain from different sources (app copy and system of record) | Keep one fact, built on the system of record. Keep the other only as a reconciliation test until it can be retired. |
| A table at a finer grain made by joining a dimension in (one row per appointment per staff member) | Retire it; a join to the dimension gives the same answer. |
| An entity table and a filtered copy (all accounts, members only) | One dimension with a flag. |
| A person-grain funnel table and a separate journey table that repeats its milestone dates | One accumulating snapshot. |
| Pre-aggregated tables (daily totals, curves, rates) over a fact that already exists | Replace with a semantic view or metric layer once a BI tool no longer needs the table. |
| Payload tables for an application (one wide row or a nested object per entity) | Move out of the warehouse layer; they are not dimensions. |

## Names that do not match their grain

Flag every model whose name implies something other than what one row is. Examples of the pattern:

| Name implies | Row actually is | Suggested name |
|---|---|---|
| `*_events` | a daily total per entity and type | `fct_*_daily` |
| `*_visitors` | one browser or device | `*_browsers` |
| `*_logs` | one row per entity per day per category | name the real grain |
| `fact__*`, `*_final`, `*_data`, `*_v2` | anything | `fct_<what one row is>` |

## Before calling something a gap

Profile the source. Fill rate, distinct values and date range take one query and regularly overturn a
"we do not record that". For example, a scheduling system often records who booked an appointment and
when its status last changed, even when an earlier analysis said those fields did not exist.

Also check for rows that are not what the table name implies (calendar blockers mixed with appointments,
test accounts mixed with customers). The fact table's grain sentence must say what it excludes.

## Things that bite

- BI tools that read legacy tables or developer databases directly. Note them as a gap; any number on
  those dashboards can disagree with the warehouse.
- Tables dropped and recreated by an outside job lose their grants. Note the dependency; do not design on
  top of a table nobody owns.
- Objects left behind by removed models still answer queries. List them for dropping.
