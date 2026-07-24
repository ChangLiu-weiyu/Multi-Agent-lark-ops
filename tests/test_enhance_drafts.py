"""Tests for the department-agent draft enrichment layer."""

from __future__ import annotations

import json
from unittest.mock import patch

from multi_agent_lark_ops.memory import AgentMemoryStore
from multi_agent_lark_ops.state import RoutingDecision, TaskDraft, WorkflowState, WorkItem
from multi_agent_lark_ops.workflows.enhance_drafts import (
    enrich_task_draft_with_ai,
    enrich_task_draft_with_rules,
    enhance_task_drafts_with_rules,
)
from multi_agent_lark_ops.workflows.task_drafts import render_task_drafts_markdown


def _sample_draft(role_key: str = "education") -> TaskDraft:
    return TaskDraft(
        summary="设计 AI 课程试讲课件",
        description="教务组需要完成 AI 课程试讲课件的设计。",
        role_key=role_key,
        source="test-doc",
        confidence=0.9,
        routing_reason="Education task.",
    )


def _sample_state() -> WorkflowState:
    return WorkflowState(
        task_drafts=[
            _sample_draft("education"),
            TaskDraft(
                summary="对接学校合作渠道",
                description="外联组需要对接学校合作渠道。",
                role_key="outreach",
                source="test-doc",
                confidence=0.85,
                routing_reason="Outreach task.",
            ),
        ]
    )


# --- Rules enrichment ---


def test_rules_enrichment_adds_fields() -> None:
    draft = _sample_draft()
    enhanced = enrich_task_draft_with_rules(draft)

    assert enhanced.enhanced is True
    assert enhanced.enhanced_by == "education"
    assert enhanced.suggested_owner != ""
    assert len(enhanced.collaborators) > 0
    assert len(enhanced.acceptance_criteria) > 0
    assert len(enhanced.dependencies) > 0
    assert len(enhanced.risk_notes) > 0


def test_rules_enrichment_appends_acceptance_criteria_to_description() -> None:
    draft = _sample_draft()
    enhanced = enrich_task_draft_with_rules(draft)

    assert "Acceptance criteria:" in enhanced.description


def test_rules_enrichment_uses_role_defaults() -> None:
    draft = _sample_draft("pr")
    enhanced = enrich_task_draft_with_rules(draft)

    assert enhanced.enhanced_by == "pr"
    assert "pr" in enhanced.suggested_owner.lower() or "PR" in enhanced.suggested_owner


def test_rules_enrichment_preserves_existing_fields() -> None:
    draft = _sample_draft()
    draft = draft.__class__(
        **{**draft.__dict__,
           "suggested_owner": "刘星言",
           "collaborators": ("operations",),
           "acceptance_criteria": ("课件通过试讲审核",),
           "dependencies": ("设备到位",),
           "risk_notes": ("时间紧张",),
           }
    )
    enhanced = enrich_task_draft_with_rules(draft)

    assert enhanced.suggested_owner == "刘星言"
    assert enhanced.collaborators == ("operations",)
    assert enhanced.acceptance_criteria == ("课件通过试讲审核",)
    assert enhanced.dependencies == ("设备到位",)
    assert enhanced.risk_notes == ("时间紧张",)


def test_enhance_task_drafts_with_rules_enriches_all() -> None:
    state = _sample_state()
    enhanced_state = enhance_task_drafts_with_rules(state)

    assert all(d.enhanced for d in enhanced_state.task_drafts)
    assert len(enhanced_state.task_drafts) == 2


# --- AI enrichment (mocked) ---


def test_ai_enrichment_with_mocked_model(tmp_path) -> None:
    mock_response = json.dumps({
        "description": "教务组需完成 AI 课程试讲课件设计，确保内容覆盖 vibe coding 和 AI 做视频。",
        "suggested_owner": "教务组负责人",
        "collaborators": ["operations", "pr"],
        "acceptance_criteria": ["课件内容覆盖 vibe coding", "试讲通过审核", "设备清单确认"],
        "dependencies": ["课程大纲定稿", "设备到位"],
        "risk_notes": ["时间紧张，需提前排期"],
    })

    from multi_agent_lark_ops.config import Settings
    settings = Settings(
        model_api_key="test-key",
        model_base_url="https://test.example.com",
        model_name="deepseek-v4-flash",
        deepseek_api_key="test-key",
        deepseek_model="deepseek-v4-flash",
        semantic_scholar_api_key=None,
        openalex_api_key=None,
        lark_cli_path="lark-cli",
        lark_cli_profile=None,
    )

    memory_root = tmp_path / "agents"
    education_dir = memory_root / "education"
    education_dir.mkdir(parents=True)
    (education_dir / "profile.md").write_text("Education agent profile", encoding="utf-8")
    store = AgentMemoryStore(root=memory_root)

    with patch("multi_agent_lark_ops.workflows.enhance_drafts._request_model", return_value=mock_response):
        draft = _sample_draft()
        enhanced = enrich_task_draft_with_ai(draft, settings=settings, memory_store=store)

    assert enhanced.enhanced is True
    assert enhanced.enhanced_by == "education"
    assert "vibe coding" in enhanced.description
    assert enhanced.suggested_owner == "教务组负责人"
    assert "operations" in enhanced.collaborators
    assert len(enhanced.acceptance_criteria) == 3
    assert len(enhanced.risk_notes) == 1


# --- Render enhanced drafts ---


def test_render_enhanced_drafts_markdown() -> None:
    draft = _sample_draft()
    enhanced = enrich_task_draft_with_rules(draft)

    rendered = render_task_drafts_markdown([enhanced])

    assert "Enhanced Fields" in rendered
    assert "Suggested owner" in rendered
    assert "Collaborators" in rendered
    assert "Acceptance criteria" in rendered
    assert "Dependencies" in rendered
    assert "Risk notes" in rendered


def test_render_non_enhanced_drafts_no_extra_section() -> None:
    draft = _sample_draft()
    rendered = render_task_drafts_markdown([draft])

    assert "Enhanced Fields" not in rendered

