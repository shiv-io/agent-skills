# Modelling rules

## Choosing the core facts

Most question sets for an operating business reduce to a handful of shapes. Look for one core fact per
shape that the questions need:

| Shape | Kimball type | Typical grain | Answers |
|---|---|---|---|
| The unit of work | Transaction or accumulating snapshot | One appointment, order, shipment, claim, ticket | Volumes, outcomes, rates, lead times, per-staff workload |
| The unit a rate is measured on, when it differs from the unit of work | Transaction | One booked slot, one attempt, one send | Occurrence, completion, success rates where a retry or move creates a new unit |
| The entity's lifecycle | Accumulating snapshot | One person, account or referral, with a timestamp per milestone | Funnel conversion, time-bound conversion ("within 7 days"), visit-N-to-N+1 retention, cohorts |
| The population over time | Periodic snapshot | One entity per month (or week) | Active counts, cumulative counts, churn, month-over-month retention, revenue per period |
| Supply or capacity | Periodic snapshot | One resource per day | Availability, wait to first slot, utilisation |

Then count. For each candidate, list the questions it is the primary table for. The core set is right when a limited set of facts carries about 80-90% of the questions — how many that is differs for every business, so don't aim for a particular count. If one candidate carries almost nothing,
demote it to supporting. If many questions need a join of two facts to answer, a core fact is missing a
column (usually a milestone or a count rolled up from another fact).

Supporting facts answer narrower questions (change history, messages, feedback, billing lines,
eligibility checks) and feed rolled-up columns into the core facts.

## Grain

- State the grain as one sentence that starts "One row per ...", and say what is left out ("calendar
  blockers and test accounts are left out").
- Every table has a primary key, single or composite, and the spec names it.
- Do not mix grains. A daily total is not an event table; name it `_daily`.

## Accumulating snapshots

- One timestamp column per milestone: `account_created_at`, `first_booked_at`, `visit_1_at` ... `visit_5_at`.
- One whole-days column per window the business uses: `days_landing_to_account`,
  `days_visit_1_to_visit_2`. The semantic layer applies the window; the table stores the gap.
- One observed-since column (`days_observed_since_<anchor>`) so a time-bound rate counts only entities
  observed for the full window, and cohorts can be marked baked or baking.
- Store a cohort key (`<anchor>_week_on`, `<anchor>_month_on`) with the week start the business uses.

## Periodic snapshots

- Start each entity's rows at the earliest month any question needs (often account creation, not first
  purchase), so funnel-stage-by-month questions work.
- Carry the status flags each competing definition needs (`is_active` and `is_engaged`) rather than
  forcing one rule before the business agrees. Record the choice as a decision.
- Flag the current, incomplete period (`is_month_complete`).

## Dimensions

- Conformed: one table per entity, shared by every fact.
- Role-playing: one dimension joined in several roles gets one key column per role on the fact
  (`referral_program_client_id`, `health_plan_client_id`). Say in the decision list which role a headline
  metric uses.
- Definitional dimensions: small, seed-backed tables that hold a rule once. An outcome dimension says
  which statuses are final and which count as lost. An appointment-type dimension says which types are
  billable. A campaign dimension says which traffic is a bot.
- Store stable facts, not derived ones that drift: birth year, not age.
- Always include a date dimension with the week start the business uses and named analysis periods.

## Reuse before building

For each target table, cite what it is built from. Prefer, in order: rename an existing model, extend
it, merge two into one, fold in a model from an open PR, build new. Every current model gets an action in
the "Current models" list, including the ones the design leaves alone.

## Naming

- `fct_` for facts, `dim_` for dimensions, `bridge_` for bridge tables. Match the client's convention if
  it already has one.
- The name says what one row is: `fct_appointment_slots`, `fct_member_monthly_status`.
- Columns: `_at` timestamp, `_on` date, `_id` key, `is_`/`was_`/`has_` boolean, the unit as a suffix
  (`_usd`, `_mins`, `_days`, `_pct` for 0-100). Keep families consistent (`visit_1_at` ... `visit_5_at`).
- When a current name disagrees with its content, propose the new name and say what the old one implied.

## Descriptions

Write for a business user. One sentence per column, two when there is a trap.

- Say what one value means, not how it is computed.
- State the unit and the fallback ("Null for self-pay", "0 where none were offered").
- Name the trap ("The source does not separate 'said no' from 'never answered'").
- Never write row counts, date ranges, "currently", "today", or claims that are only true of the data
  as it stands. Never write real names, emails or identifiers, even as examples.

## Column status values

| Status | Meaning |
|---|---|
| `Exists` | Same name, same meaning, in a current model. |
| `Rename` | Exists under another name; the lineage column names it. |
| `PR #nn` or `Branch` | Exists on an open pull request or branch. |
| `New` | Has a source today and needs building. |
| `Gap Gnn` | Stays null until gap Gnn closes. |

## Gaps and decisions

- A **gap** is missing data. Give it an id, the questions it blocks, the team that can close it, a status
  (open, partly closed, in flight, closed, new) and the evidence. Say "proved" or "guess" in the evidence.
- A **decision** is an ambiguous definition. Give the options and a recommended default. Decisions that
  change a headline number go first.
- Readiness follows from both: a question is Ready when every column it needs has a source, Partial when
  some columns wait on a gap or decision, Blocked when its core source does not exist yet.
