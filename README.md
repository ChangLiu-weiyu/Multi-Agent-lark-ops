# Multi-Agent Lark Ops

Multi-Agent Lark Ops is a configurable multi-agent workflow system for Lark/Feishu team operations.

It reads Lark documents, extracts actionable work items, routes them to role agents, and produces human-reviewable task drafts. The current implementation is designed for Yubing-style organizational workflows such as education, operations, outreach, PR, academic output, and competition planning.

## What It Does

- Reads Docx/Wiki content through the local `lark-cli`.
- Extracts near-term tasks from sections like `近期待办` and `近期重点`.
- Routes tasks to role-based agents.
- Supports both deterministic rules and AI-backed analysis.
- Generates review-only Lark task drafts.
- Keeps local, editable memory for each agent.
- Uses a configurable agent registry instead of hardcoding every role in code.

## Current Architecture

```text
Lark document -> LarkClient -> workflow selector
-> extractor / router / AI analyzer -> task drafts -> human review
```

The current codebase is organized around these layers:

- `src/multi_agent_lark_ops/cli.py`: command-line entry points
- `src/multi_agent_lark_ops/lark/`: local `lark-cli` adapter
- `src/multi_agent_lark_ops/workflows/`: extraction, routing, AI analysis, task drafts
- `src/multi_agent_lark_ops/roles.py`: role definitions and routing metadata
- `src/multi_agent_lark_ops/memory.py`: file-based agent memory
- `config/agents.json`: machine-readable agent configuration
- `memory/agents/<role_key>/`: profile, episodes, knowledge

## Status

Implemented:

- Lark document fetching
- Rules-based task extraction and routing
- AI-backed task extraction and routing via an OpenAI-compatible endpoint
- Review-only task draft generation
- Configurable agent roles
- File-based agent memory
- Local Markdown work logs and diagrams

Not yet implemented:

- Writing approved tasks back to Lark
- Message posting / notifications
- Human approval automation
- Full multi-agent enrichment layer for each department

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

Compare with deterministic routing:

```powershell
python -m multi_agent_lark_ops.cli --draft-tasks-rules "<Lark document URL>"
```

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

The current codebase is covered by unit tests and was last verified with 15 passing tests.

## Roadmap

1. Add the department-agent enrichment layer.
2. Turn review-only drafts into approved write candidates.
3. Add a Lark task writer after human confirmation.
4. Feed historical episodes back into each agent's memory.
5. Add richer writeback targets such as tasks, messages, and follow-up notes.
