# Agent Memory

This directory stores local, human-readable memory for each role agent.

Current memory layout per agent:

- profile.md: stable identity, responsibilities, routing hints, and output preferences.
- episodes.jsonl: append-only historical work records. One JSON object per line.
- knowledge/README.md: stable SOPs, templates, examples, and reference links.

The first version is intentionally file-based so it is auditable and easy to edit. A vector store can be added later after enough episodes and knowledge files accumulate.
