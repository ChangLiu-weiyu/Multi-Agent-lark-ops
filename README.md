# Multi-Agent Lark Ops

Multi-Agent Lark Ops is a configurable multi-agent workflow system for Lark/Feishu team operations.

It reads Lark documents, extracts actionable work items, routes them to role agents, enriches the drafts with department-specific context, exports human-reviewable task bundles, writes approved tasks to Lark behind an explicit confirmation gate, and records outcomes into each department agent's memory.

## What It Does

- Reads Docx/Wiki content through the local `lark-cli`.
- Extracts near-term tasks from sections like `近期待办` and `近期重点`.
- Routes tasks to role-based agents.
- Supports both deterministic rules and AI-backed analysis.
- Generates review-only Lark task drafts.
- Adds a department-agent enrichment layer for owners, collaborators, acceptance criteria, dependencies, and risk notes.
- Exports review bundles as JSON and Markdown before any Lark writeback.
- Parses approved review JSON and previews `lark-cli task +create --dry-run` commands.
- Writes approved tasks to Lark only after `--confirm-writeback` is provided.
- Marks successful writebacks back into the review JSON as `written_to_lark`.
- Records review and writeback outcomes into per-agent `episodes.jsonl` memory.
- Uses a configurable agent registry instead of hardcoding every role in code.

## Current Architecture

```text
Lark document -> LarkClient -> workflow selector
-> extractor / router / AI analyzer -> task drafts -> department-agent enrichment -> review bundle -> approved writeback gate -> Lark task creation -> review JSON reconciliation -> agent memory reconciliation
```

The current codebase is organized around these layers:

- `src/multi_agent_lark_ops/cli.py`: command-line entry points
- `src/multi_agent_lark_ops/lark/`: local `lark-cli` adapter
- `src/multi_agent_lark_ops/workflows/`: extraction, routing, AI analysis, task drafts, enrichment, review export, writeback
- `src/multi_agent_lark_ops/roles.py`: role definitions and routing metadata
- `src/multi_agent_lark_ops/memory.py`: file-based agent memory
- `config/agents.json`: machine-readable agent configuration
- `memory/agents/<role_key>/`: profile, episodes, knowledge
- `outputs/task_drafts/`: generated review files, ignored by Git

## Status

Implemented:

- Lark document fetching
- Rules-based task extraction and routing
- AI-backed task extraction and routing via an OpenAI-compatible endpoint
- Review-only task draft generation
- Department-agent draft enrichment
- JSON/Markdown review bundle export
- Approved review parsing
- Dry-run Lark task writeback preview
- Confirmed Lark task writeback
- Review JSON reconciliation to `written_to_lark`
- Agent memory reconciliation into `episodes.jsonl`
- Configurable agent roles
- File-based agent memory
- Local Markdown work logs and diagrams

Not yet implemented:

- Message posting / notifications
- Human approval automation
- Richer writeback targets such as messages and follow-up notes

## Quick Start

```powershell
$env:PYTHONPATH="src"
python -m multi_agent_lark_ops.cli --help
```

Read a document:

```powershell
python -m multi_agent_lark_ops.cli --fetch-doc "<Lark document URL>"
```

Generate review-only task drafts:

```powershell
python -m multi_agent_lark_ops.cli --draft-tasks-ai "<Lark document URL>"
```

Enrich task drafts with department-agent fields:

```powershell
python -m multi_agent_lark_ops.cli --enhance-drafts-ai "<Lark document URL>"
```

Export enhanced drafts for human review:

```powershell
python -m multi_agent_lark_ops.cli --export-review-ai "<Lark document URL>"
```

The export command writes a `.json` file for later programmatic writeback and a `.md` file for human review. By default, both files are written under `outputs/task_drafts/`.

After a human changes task statuses in the JSON to `approved` or `ready_to_write`, preview Lark task creation:

```powershell
python -m multi_agent_lark_ops.cli --write-approved-tasks-dry-run "outputs/task_drafts/<review-id>.json"
```

To actually write approved tasks, pass the confirmation gate:

```powershell
python -m multi_agent_lark_ops.cli --write-approved-tasks "outputs/task_drafts/<review-id>.json" --confirm-writeback
```

Compare with deterministic routing:

```powershell
python -m multi_agent_lark_ops.cli --export-review-rules "<Lark document URL>"
```

## Review Statuses

Review JSON tasks use one of these statuses:

- `needs_human_review`
- `approved`
- `rejected`
- `needs_revision`
- `ready_to_write`
- `written_to_lark`

Only `approved` and `ready_to_write` tasks are selected by the writeback commands.

## AI Mode

The current AI reasoning layer uses an OpenAI-compatible chat endpoint. The default model is `deepseek-v4-flash`.

Environment variables:

```powershell
OPENAI_PROXY_BASE_URL=https://openai-proxy.miracleplus.com
DEEPSEEK_API_KEY=<your key>
DEEPSEEK_MODEL=deepseek-v4-flash
```

`DEEPSEEK_API_KEY` is preferred. `GPT_API_KEY` is accepted as a fallback when you want to reuse the same key under a different name.

## Configuration And Memory

Agent definitions are tunable without changing code:

- `config/agents.json` for runtime loading
- `config/agents.yaml` for human editing reference

Each agent has local memory under:

- `memory/agents/<role_key>/profile.md`
- `memory/agents/<role_key>/episodes.jsonl`
- `memory/agents/<role_key>/knowledge/`

This keeps the first version readable, auditable, and easy to revise.

## Development Notes

Project diagrams and progress notes live under `worklog/`:

- [organization-chart.md](worklog/organization-chart.md)
- [task-flow-chart.md](worklog/task-flow-chart.md)
- [system-architecture.md](worklog/system-architecture.md)
- [development-progress.md](worklog/development-progress.md)

## Verification

The current codebase is covered by unit tests and was last verified with 46 passing tests.

## Roadmap

1. Add richer writeback targets such as messages and follow-up notes.
2. Add explicit notification / handoff flows around confirmed writeback.
