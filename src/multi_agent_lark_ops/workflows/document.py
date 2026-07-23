"""Document-level workflow helpers."""

from __future__ import annotations

from multi_agent_lark_ops.config import Settings, load_settings
from multi_agent_lark_ops.state import WorkflowState
from multi_agent_lark_ops.workflows.ai import analyze_document_with_ai_or_fallback
from multi_agent_lark_ops.workflows.document_rules import analyze_document_with_rules
from multi_agent_lark_ops.workflows.task_drafts import attach_task_drafts


def dispatch_document_text(
    document_text: str,
    *,
    source: str = "lark-doc",
    settings: Settings | None = None,
) -> WorkflowState:
    current_settings = settings or load_settings()
    if current_settings.has_model_credentials:
        return attach_task_drafts(
            analyze_document_with_ai_or_fallback(document_text, settings=current_settings, source=source)
        )
    return attach_task_drafts(analyze_document_with_rules(document_text, source=source))


def dispatch_document_text_rules(document_text: str, *, source: str = "lark-doc") -> WorkflowState:
    return attach_task_drafts(analyze_document_with_rules(document_text, source=source))


def dispatch_document_text_ai(
    document_text: str,
    *,
    source: str = "lark-doc",
    settings: Settings | None = None,
) -> WorkflowState:
    current_settings = settings or load_settings()
    return attach_task_drafts(
        analyze_document_with_ai_or_fallback(document_text, settings=current_settings, source=source)
    )
