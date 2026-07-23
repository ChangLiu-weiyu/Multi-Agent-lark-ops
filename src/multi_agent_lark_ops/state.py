"""Shared state models used by workflows and agents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WorkItem:
    title: str
    detail: str = ""
    source: str = "manual"
    assigned_role: str | None = None


@dataclass(frozen=True)
class RoutingDecision:
    work_item: WorkItem
    role_key: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class TaskDraft:
    summary: str
    description: str
    role_key: str
    source: str
    confidence: float
    routing_reason: str
    assignee_open_id: str | None = None
    due: str | None = None
    tasklist_id: str | None = None
    review_status: str = "needs_human_review"


@dataclass
class WorkflowState:
    source_document_token: str | None = None
    source_text: str = ""
    work_items: list[WorkItem] = field(default_factory=list)
    routing_decisions: list[RoutingDecision] = field(default_factory=list)
    task_drafts: list[TaskDraft] = field(default_factory=list)
    analysis_mode: str = "rules"
    analysis_model: str | None = None
    needs_human_review: bool = True
