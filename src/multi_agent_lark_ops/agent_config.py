"""Load configurable agent definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_agents_config_path() -> Path:
    return project_root() / "config" / "agents.json"


def load_agents_config(path: Path | None = None) -> list[dict[str, Any]]:
    config_path = path or default_agents_config_path()
    with config_path.open(encoding="utf-8") as file:
        data = json.load(file)
    agents = data.get("agents")
    if not isinstance(agents, list):
        raise ValueError(f"Invalid agents config: {config_path}")
    return agents
