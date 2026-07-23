"""File-based memory store for role agents."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multi_agent_lark_ops.agent_config import project_root


@dataclass(frozen=True)
class AgentEpisode:
    role_key: str
    event_type: str
    summary: str
    source: str
    data: dict[str, Any]
    created_at: str


class AgentMemoryStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or project_root() / "memory" / "agents"

    def agent_dir(self, role_key: str) -> Path:
        return self.root / role_key

    def profile_path(self, role_key: str) -> Path:
        return self.agent_dir(role_key) / "profile.md"

    def episodes_path(self, role_key: str) -> Path:
        return self.agent_dir(role_key) / "episodes.jsonl"

    def knowledge_dir(self, role_key: str) -> Path:
        return self.agent_dir(role_key) / "knowledge"

    def read_profile(self, role_key: str) -> str:
        return self.profile_path(role_key).read_text(encoding="utf-8")

    def append_episode(
        self,
        *,
        role_key: str,
        event_type: str,
        summary: str,
        source: str,
        data: dict[str, Any] | None = None,
    ) -> AgentEpisode:
        self.agent_dir(role_key).mkdir(parents=True, exist_ok=True)
        episode = AgentEpisode(
            role_key=role_key,
            event_type=event_type,
            summary=summary,
            source=source,
            data=data or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self.episodes_path(role_key).open("a", encoding="utf-8") as file:
            file.write(json.dumps(asdict(episode), ensure_ascii=False) + "\n")
        return episode

    def read_recent_episodes(self, role_key: str, *, limit: int = 5) -> list[AgentEpisode]:
        path = self.episodes_path(role_key)
        if not path.exists():
            return []
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent = lines[-limit:]
        return [AgentEpisode(**json.loads(line)) for line in recent]
