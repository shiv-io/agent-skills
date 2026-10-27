# agent-skills

Private agent skills in the portable [Agent Skills](https://www.skills.sh/docs) format. Each skill is a
folder under `skills/` with a `SKILL.md`, and optional `scripts/`, `references/` and `assets/`.

| Skill | What it does |
|---|---|
| [`dimensional-warehouse-design`](skills/dimensional-warehouse-design/SKILL.md) | Turns client source documents (KPI spreadsheets, metric memos, tickets, business questions) and the current warehouse into a Kimball design: a hyperlinked Excel workbook with one tab per table, a business-question map, a bus matrix and a keep/rename/retire list, plus Excalidraw diagrams. |

## Install

The repository is private. The `skills` CLI uses your existing Git or GitHub CLI credentials.

```bash
# every skill, globally, for Claude Code
npx skills add shiv-io/agent-skills -g -a claude-code -y

# one skill, for several agents
npx skills add shiv-io/agent-skills -g -s dimensional-warehouse-design -a claude-code -a codex

# update later
npx skills update -g
```

Claude Code installs into `$CLAUDE_CONFIG_DIR/skills`, or `~/.claude/skills` when that variable is unset.
Run the command once per config directory you use.

## Rules for this repository

- No client data. Specs, spreadsheets, outputs and notes from a client engagement stay in that client's
  project. Examples here are fictional.
- Scripts declare their dependencies inline and run with `uv run`, so a skill works without a shared
  environment.
