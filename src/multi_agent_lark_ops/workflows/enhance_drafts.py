"""Department-agent draft enrichment."""

from __future__ import annotations

import json
from dataclasses import replace

from pydantic import BaseModel, Field, ValidationError

from multi_agent_lark_ops.config import Settings
from multi_agent_lark_ops.memory import AgentMemoryStore
from multi_agent_lark_ops.roles import AgentRole, get_role
from multi_agent_lark_ops.state import TaskDraft, WorkflowState
from multi_agent_lark_ops.workflows.ai import _request_model


class EnhancedDraftPayload(BaseModel):
    description: str
    suggested_owner: str = ""
    collaborators: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)


def _knowledge_summary(memory_store: AgentMemoryStore, role_key: str) -> str:
    readme = memory_store.knowledge_dir(role_key) / "README.md"
    if readme.exists():
        return readme.read_text(encoding="utf-8")
    return ""


def _episodes_summary(memory_store: AgentMemoryStore, role_key: str) -> str:
    episodes = memory_store.read_recent_episodes(role_key, limit=5)
    if not episodes:
        return "No recent episodes."
    return "\n".join(
        f"- {episode.created_at} {episode.event_type}: {episode.summary}"
        for episode in episodes
    )


def enrich_task_draft_with_rules(draft: TaskDraft, *, memory_store: AgentMemoryStore | None = None) -> TaskDraft:
    role = get_role(draft.role_key)
    collaborators = draft.collaborators or role.default_collaborators
    acceptance = draft.acceptance_criteria or tuple(
        f"Complete and review {field.replace('_', ' ')}" for field in role.draft_fields[:3]
    )
    if not acceptance:
        acceptance = ("Task is clarified and ready for human review.",)

    suggested_owner = draft.suggested_owner or f"{role.name} owner"
    dependencies = draft.dependencies or collaborators
    risk_notes = draft.risk_notes or ("Confirm owner and deadline before creating the Lark task.",)
    description = draft.description
    if "Acceptance criteria:" not in description:
        description = "\n".join(
            [
                description,
                "",
                "Acceptance criteria:",
                *[f"- {item}" for item in acceptance],
            ]
        )

    return replace(
        draft,
        description=description,
        suggested_owner=suggested_owner,
        collaborators=tuple(collaborators),
        acceptance_criteria=tuple(acceptance),
        dependencies=tuple(dependencies),
        risk_notes=tuple(risk_notes),
        enhanced=True,
        enhanced_by=role.key,
    )


def _prompt_for_agent(
    *,
    role: AgentRole,
    draft: TaskDraft,
    profile: str,
    recent_episodes: str,
    knowledge: str,
) -> list[dict[str, str]]:
    system = (
        f"You are {role.name}, a department agent in a multi-agent Lark operations system. "
        "Enhance one task draft for human review. Return JSON only."
    )
    user = f"""
Agent profile:
{profile}

Recent memory episodes:
{recent_episodes}

Knowledge notes:
{knowledge}

Task draft:
- summary: {draft.summary}
- description: {draft.description}
- role_key: {draft.role_key}
- source: {draft.source}
- routing_reason: {draft.routing_reason}

Return JSON with this shape:
{{
  "description": "improved task description",
  "suggested_owner": "owner hint, not a fabricated person",
  "collaborators": ["role keys or group names"],
  "acceptance_criteria": ["clear checklist items"],
  "dependencies": ["prerequisites or needed inputs"],
  "risk_notes": ["risks or confirmation points"]
}}

Rules:
- Do not invent specific assignee names unless they are already present in the task text.
- Keep the output suitable for human review before creating a Lark task.
- Use Chinese for task content.
- Be concrete and concise.
""".strip()
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def enrich_task_draft_with_ai(
    draft: TaskDraft,
    *,
    settings: Settings,
    memory_store: AgentMemoryStore | None = None,
) -> TaskDraft:
    role = get_role(draft.role_key)
    store = memory_store or AgentMemoryStore()
    content = _request_model(
        settings,
        _prompt_for_agent(
            role=role,
            draft=draft,
            profile=store.read_profile(role.key),
            recent_episodes=_episodes_summary(store, role.key),
            knowledge=_knowledge_summary(store, role.key),
        ),
    )
    try:
        payload = EnhancedDraftPayload.model_validate_json(content)
    except ValidationError:
        try:
            payload_data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Model output was not valid enhanced draft JSON") from exc
        payload = EnhancedDraftPayload.model_validate(payload_data)

    enhanced = replace(
        draft,
        description=payload.description,
        suggested_owner=payload.suggested_owner,
        collaborators=tuple(payload.collaborators),
        acceptance_criteria=tuple(payload.acceptance_criteria),
        dependencies=tuple(payload.dependencies),
        risk_notes=tuple(payload.risk_notes),
        enhanced=True,
        enhanced_by=role.key,
    )
    store.append_episode(
        role_key=role.key,
        event_type="draft_enhanced",
        summary=enhanced.summary,
        source=enhanced.source,
        data={"confidence": enhanced.confidence, "mode": "ai"},
    )
    return enhanced


def enhance_task_drafts_with_rules(
    state: WorkflowState,
    *,
    memory_store: AgentMemoryStore | None = None,
) -> WorkflowState:
    state.task_drafts = [
        enrich_task_draft_with_rules(draft, memory_store=memory_store)
        for draft in state.task_drafts
    ]
    return state


def enhance_task_drafts_with_ai(
    state: WorkflowState,
    *,
    settings: Settings,
    memory_store: AgentMemoryStore | None = None,
) -> WorkflowState:
    state.task_drafts = [
        enrich_task_draft_with_ai(draft, settings=settings, memory_store=memory_store)
        for draft in state.task_drafts
    ]
    return state


def enhance_task_drafts_auto(
    state: WorkflowState,
    *,
    settings: Settings,
    memory_store: AgentMemoryStore | None = None,
) -> WorkflowState:
    if settings.has_model_credentials:
        try:
            return enhance_task_drafts_with_ai(state, settings=settings, memory_store=memory_store)
        except Exception:
            return enhance_task_drafts_with_rules(state, memory_store=memory_store)
    return enhance_task_drafts_with_rules(state, memory_store=memory_store)
