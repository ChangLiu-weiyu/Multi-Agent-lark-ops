"""Tests for human review bundle exports."""

from __future__ import annotations

import json

import pytest

from multi_agent_lark_ops.state import TaskDraft, WorkflowState
from multi_agent_lark_ops.workflows.review import (
    VALID_REVIEW_STATUSES,
    build_review_bundle,
    export_review_bundle,
    render_review_bundle_markdown,
    review_bundle_to_dict,
    update_draft_review_status,
)


def _draft() -> TaskDraft:
    return TaskDraft(
        summary="设计 AI 课程试讲课件",
        description="教务组需要完成 AI 课程试讲课件设计。",
        role_key="education",
        source="doc-url",
        confidence=0.91,
        routing_reason="Education task.",
        suggested_owner="教务组负责人",
        collaborators=("operations",),
        acceptance_criteria=("试讲通过审核",),
        dependencies=("设备到位",),
        risk_notes=("确认截止时间",),
        enhanced=True,
        enhanced_by="education",
    )


def _state() -> WorkflowState:
    return WorkflowState(
        source_document_token="doc-token",
        task_drafts=[_draft()],
        analysis_mode="rules",
        analysis_model=None,
    )


def test_update_draft_review_status_accepts_valid_status() -> None:
    draft = _draft()

    updated = update_draft_review_status(draft, "approved")

    assert updated.review_status == "approved"
    assert draft.review_status == "needs_human_review"


def test_update_draft_review_status_rejects_invalid_status() -> None:
    with pytest.raises(ValueError):
        update_draft_review_status(_draft(), "maybe")


def test_build_review_bundle_from_state() -> None:
    bundle = build_review_bundle(
        _state(),
        bundle_id="review-test",
        created_at="2026-07-24T00:00:00+00:00",
    )

    assert bundle.bundle_id == "review-test"
    assert bundle.source == "doc-token"
    assert bundle.analysis_mode == "rules"
    assert bundle.needs_human_review is True
    assert len(bundle.drafts) == 1


def test_review_bundle_to_dict_has_stable_shape() -> None:
    bundle = build_review_bundle(_state(), bundle_id="review-test", created_at="2026-07-24T00:00:00+00:00")

    payload = review_bundle_to_dict(bundle)

    assert payload["schema_version"] == 1
    assert payload["bundle_id"] == "review-test"
    assert payload["allowed_statuses"] == list(VALID_REVIEW_STATUSES)
    assert payload["tasks"][0]["review_id"] == "001-education"
    assert payload["tasks"][0]["summary"] == "设计 AI 课程试讲课件"
    assert payload["tasks"][0]["enhanced"] is True


def test_render_review_bundle_markdown_includes_review_context() -> None:
    bundle = build_review_bundle(_state(), bundle_id="review-test", created_at="2026-07-24T00:00:00+00:00")

    rendered = render_review_bundle_markdown(bundle)

    assert "# Task Review Bundle" in rendered
    assert "review-test" in rendered
    assert "Review Statuses" in rendered
    assert "Lark Task Drafts" in rendered
    assert "设计 AI 课程试讲课件" in rendered


def test_export_review_bundle_writes_json_and_markdown(tmp_path) -> None:
    bundle = build_review_bundle(_state(), bundle_id="review-test", created_at="2026-07-24T00:00:00+00:00")

    export = export_review_bundle(bundle, output_dir=tmp_path)

    assert export.json_path.exists()
    assert export.markdown_path.exists()
    assert export.json_path.name == "review-test.json"
    assert export.markdown_path.name == "review-test.md"

    payload = json.loads(export.json_path.read_text(encoding="utf-8"))
    assert payload["bundle_id"] == "review-test"
    assert payload["tasks"][0]["review_status"] == "needs_human_review"
    assert "Task Review Bundle" in export.markdown_path.read_text(encoding="utf-8")
