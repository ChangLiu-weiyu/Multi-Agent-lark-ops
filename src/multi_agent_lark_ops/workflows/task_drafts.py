"""Create human-reviewable Lark task drafts from routed work items."""

from __future__ import annotations

from collections.abc import Iterable

from multi_agent_lark_ops.roles import get_role
from multi_agent_lark_ops.state import RoutingDecision, TaskDraft, WorkflowState


def build_task_draft(decision: RoutingDecision) -> TaskDraft:
    role = get_role(decision.role_key)
    detail = decision.work_item.detail.strip()
    description_lines = [
        f"Suggested agent: {role.name}",
        f"Routing reason: {decision.reason}",
        f"Source: {decision.work_item.source}",
    ]
    if detail:
        description_lines.insert(0, detail)

    return TaskDraft(
        summary=decision.work_item.title,
        description="\n".join(description_lines),
        role_key=decision.role_key,
        source=decision.work_item.source,
        confidence=decision.confidence,
        routing_reason=decision.reason,
    )


def build_task_drafts(decisions: Iterable[RoutingDecision]) -> list[TaskDraft]:
    return [build_task_draft(decision) for decision in decisions]


def attach_task_drafts(state: WorkflowState) -> WorkflowState:
    state.task_drafts = build_task_drafts(state.routing_decisions)
    return state


def render_task_drafts_markdown(task_drafts: Iterable[TaskDraft]) -> str:
    lines = [
        "# Lark Task Drafts",
        "",
        "These are review-only drafts. No Lark tasks have been created.",
    ]
    for index, draft in enumerate(task_drafts, start=1):
        lines.extend(
            [
                "",
                f"## {index}. {draft.summary}",
                "",
                f"- Role: `{draft.role_key}`",
                f"- Review status: `{draft.review_status}`",
                f"- Confidence: `{draft.confidence:.2f}`",
                f"- Source: {draft.source}",
                "",
                "Description:",
                "",
                draft.description,
            ]
        )
        if draft.assignee_open_id:
            lines.append(f"- Assignee: `{draft.assignee_open_id}`")
        if draft.due:
            lines.append(f"- Due: `{draft.due}`")
        if draft.tasklist_id:
            lines.append(f"- Task list: `{draft.tasklist_id}`")
    return "\n".join(lines)
