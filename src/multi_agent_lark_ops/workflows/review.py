"""Human review bundle helpers for enriched task drafts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from multi_agent_lark_ops.agent_config import project_root
from multi_agent_lark_ops.state import TaskDraft, WorkflowState
from multi_agent_lark_ops.workflows.task_drafts import render_task_drafts_markdown

VALID_REVIEW_STATUSES = (
    "needs_human_review",
    "approved",
    "rejected",
    "needs_revision",
    "ready_to_write",
    "written_to_lark",
)


@dataclass(frozen=True)
class ReviewBundle:
    bundle_id: str
    source: str
    analysis_mode: str
    analysis_model: str | None
    created_at: str
    drafts: tuple[TaskDraft, ...]
    needs_human_review: bool = True


@dataclass(frozen=True)
class ReviewExport:
    bundle: ReviewBundle
    json_path: Path
    markdown_path: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _default_bundle_id(created_at: str) -> str:
    normalized = created_at.replace(":", "").replace("-", "")
    normalized = normalized.replace("+", "Z").replace(".", "")
    return f"review-{normalized}"


def update_draft_review_status(draft: TaskDraft, status: str) -> TaskDraft:
    if status not in VALID_REVIEW_STATUSES:
        allowed = ", ".join(VALID_REVIEW_STATUSES)
        raise ValueError(f"Invalid review status '{status}'. Allowed: {allowed}")
    return replace(draft, review_status=status)


def build_review_bundle(
    state: WorkflowState,
    *,
    bundle_id: str | None = None,
    created_at: str | None = None,
) -> ReviewBundle:
    timestamp = created_at or _utc_now()
    return ReviewBundle(
        bundle_id=bundle_id or _default_bundle_id(timestamp),
        source=state.source_document_token or "lark-doc",
        analysis_mode=state.analysis_mode,
        analysis_model=state.analysis_model,
        created_at=timestamp,
        drafts=tuple(state.task_drafts),
        needs_human_review=True,
    )


def _task_to_review_dict(index: int, draft: TaskDraft) -> dict[str, Any]:
    data = asdict(draft)
    data["review_id"] = f"{index:03d}-{draft.role_key}"
    data["allowed_statuses"] = list(VALID_REVIEW_STATUSES)
    return data


def review_bundle_to_dict(bundle: ReviewBundle) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "bundle_id": bundle.bundle_id,
        "source": bundle.source,
        "analysis_mode": bundle.analysis_mode,
        "analysis_model": bundle.analysis_model,
        "created_at": bundle.created_at,
        "needs_human_review": bundle.needs_human_review,
        "allowed_statuses": list(VALID_REVIEW_STATUSES),
        "tasks": [
            _task_to_review_dict(index, draft)
            for index, draft in enumerate(bundle.drafts, start=1)
        ],
    }


def render_review_bundle_markdown(bundle: ReviewBundle) -> str:
    lines = [
        "# Task Review Bundle",
        "",
        f"- Bundle ID: `{bundle.bundle_id}`",
        f"- Source: {bundle.source}",
        f"- Analysis mode: `{bundle.analysis_mode}`",
        f"- Created at: `{bundle.created_at}`",
        "- Human review required before writing back to Lark: yes",
    ]
    if bundle.analysis_model:
        lines.append(f"- Analysis model: `{bundle.analysis_model}`")
    lines.extend(
        [
            "",
            "## Review Statuses",
            "",
            "Use one of these statuses in the JSON file before writeback:",
            "",
            *[f"- `{status}`" for status in VALID_REVIEW_STATUSES],
            "",
            render_task_drafts_markdown(bundle.drafts),
        ]
    )
    return "\n".join(lines)


def export_review_bundle(
    bundle: ReviewBundle,
    *,
    output_dir: Path | None = None,
) -> ReviewExport:
    target_dir = output_dir or project_root() / "outputs" / "task_drafts"
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / f"{bundle.bundle_id}.json"
    markdown_path = target_dir / f"{bundle.bundle_id}.md"

    json_path.write_text(
        json.dumps(review_bundle_to_dict(bundle), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown_path.write_text(render_review_bundle_markdown(bundle), encoding="utf-8")
    return ReviewExport(bundle=bundle, json_path=json_path, markdown_path=markdown_path)
